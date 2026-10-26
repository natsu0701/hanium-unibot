"""
PDF → RAG 청크 변환 서비스

Upstage 원본 응답은 UPSTAGE_CACHE_DIR 에 캐시하고, 있으면 API 를 다시 호출하지 않는다.

사용 예:
    from app.services.pdf_service import extract_pdf, save_chunks
    chunks = extract_pdf("data/raw/guide.pdf", "konkuk")
    save_chunks(chunks, "data/processed/konkuk/extracted_exp.json")

명령줄 (backend 디렉터리에서):
    .venv/bin/python -m app.services.pdf_service data/raw/guide.pdf --school-id konkuk
    .venv/bin/python -m app.services.pdf_service data/raw/guide.pdf --school-id konkuk --pages 1-24 --show-titles
"""

from __future__ import annotations

import argparse
import collections
import html
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from pypdf import PdfReader, PdfWriter

# backend/app/services/pdf_service.py → parents[2] = backend
BACKEND_DIR = Path(__file__).resolve().parents[2]
# 파일을 직접 실행할 때(python app/services/pdf_service.py)도 app 패키지를 찾도록
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.Core.logger import get_logger
from app.utils.table_parser import html_table_to_text

logger = get_logger(__name__)

load_dotenv(BACKEND_DIR / ".env")

UPSTAGE_URL = "https://api.upstage.ai/v1/document-ai/document-parse"
UPSTAGE_TIMEOUT = 300
# data/processed/ 는 .gitignore 대상이라 원본 응답 캐시도 그 아래에 둔다
UPSTAGE_CACHE_DIR = BACKEND_DIR / "data" / "processed" / "_upstage_cache"

MAX_CHUNK_LEN = 1800
PDF_PART_PAGES = 50

# 제목 판정
MAX_TITLE_LEN = 40
MAX_UNNUMBERED_TITLE_LEN = 15   # 번호(가), (1) 등) 없는 제목은 이보다 짧아야 함
MIN_HANGUL_RATIO = 0.3
# 본문으로 보는 category (제목 후보에서 제외)
BODY_CATEGORIES = {"list", "table", "equation", "caption", "footnote", "index", "chart"}
SKIP_CATEGORIES = {"figure", "image"}
# 번호 없는 짧은 줄 바로 다음에 이 요소가 오면 제목이 아니라 그림/표 설명으로 봄
CAPTION_TARGETS = {"figure", "image", "table", "chart"}
NOISE_CATEGORIES = {"header", "footer"}

# 제목-본문 병합
MERGE_MIN_LEN = 100          # 제목에 붙인 본문이 이 길이 이상이면 청크 마감
MERGE_MAX_BODIES = 3         # 제목 뒤에 붙일 본문 요소 최대 개수

# 쪽머리 반복 판정
REPEAT_MIN_PAGES = 3
MARGIN_TOP = 0.10            # 페이지 위 10% 이내
MARGIN_BOTTOM = 0.88         # 페이지 아래 12% 이내
# 반복 규칙의 보조 (반복 횟수가 모자라도 제거)
PAGE_NOISE_BLACKLIST = {"학사요람", "목차"}

# 표지·목차
DEFAULT_SKIP_PAGES = frozenset({1})   # 표지
TOC_CATEGORIES = {"index"}
TOC_DOT_MIN = 10             # 목차 점선(·····) 판정


class PdfExtractionError(RuntimeError):
    """PDF 추출(Upstage 호출 포함) 실패."""


# =========================================================
# 텍스트 유틸 (extract_pdf.py 와 동일)
# =========================================================

def clean_revision_dates(text: str) -> str:
    """개정일 표기 제거: <2024.03.01 개정>, (2024.03.01) 등."""
    patterns = [
        r"<[^>]*(개정|시행|제정|폐지|공포)[^>]*>",
        r"<\d{4}\.\d{1,2}\.\d{1,2}[^>]*>",
        r"\(\d{4}\.\d{1,2}\.\d{1,2}[^)]*\)",
    ]
    for pattern in patterns:
        text = re.sub(pattern, "", text)
    return text.strip()


def remove_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def extract_chapter(text: str) -> tuple[int | None, str | None]:
    """제9장 휴학·복학·제적 및 자퇴 → (9, "휴학·복학·제적 및 자퇴")"""
    match = re.search(r"제\s*(\d+)\s*장\s*\n?\s*(.+)", text)
    if not match:
        return None, None
    return int(match.group(1)), match.group(2).split("\n")[0].strip()


def split_long_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    """MAX_CHUNK_LEN 을 넘는 청크를 문장 단위로 나눈다."""
    text = record["text"]

    if len(text) <= MAX_CHUNK_LEN:
        return [record]

    sentences = re.split(r"(?<=[.!?。！？])\s*", text)

    chunks = []
    current_text = ""

    for sentence in sentences:
        if not sentence:
            continue

        if len(sentence) > MAX_CHUNK_LEN:
            if current_text:
                chunks.append({**record, "text": current_text.strip()})
                current_text = ""
            for i in range(0, len(sentence), MAX_CHUNK_LEN):
                chunks.append({**record, "text": sentence[i:i + MAX_CHUNK_LEN].strip()})
            continue

        if current_text and len(current_text) + len(sentence) + 1 > MAX_CHUNK_LEN:
            chunks.append({**record, "text": current_text.strip()})
            current_text = sentence
        else:
            if current_text:
                current_text += " "
            current_text += sentence

    if current_text.strip():
        chunks.append({**record, "text": current_text.strip()})

    return chunks


def build_doc_id(filename: str, school_id: str) -> str:
    """konkuk + guide.pdf → konkuk-guide"""
    name = os.path.splitext(filename)[0]
    slug = name.lower().replace(" ", "-").replace("_", "-")
    return f"{school_id}-{slug}"


# =========================================================
# Upstage 호출 (원본 응답 캐시)
# =========================================================

def _cut_pdf(pdf_path: Path, first: int, last: int) -> Path:
    """first~last 페이지(1부터)만 담은 임시 PDF."""
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    for i in range(first - 1, last):
        writer.add_page(reader.pages[i])
    temp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    writer.write(temp)
    temp.close()
    return Path(temp.name)


def _call_upstage(pdf_path: Path) -> dict[str, Any]:
    api_key = os.getenv("UPSTAGE_API_KEY")
    if not api_key:
        raise PdfExtractionError("UPSTAGE_API_KEY가 설정되지 않았습니다.")

    with pdf_path.open("rb") as file:
        try:
            response = requests.post(
                UPSTAGE_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                files={"document": file},
                data={"ocr": "auto"},
                timeout=UPSTAGE_TIMEOUT,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise PdfExtractionError(f"Upstage 호출 실패: {exc}") from exc

    return response.json()


def load_elements(
    pdf_path: Path,
    first: int,
    last: int,
    *,
    force: bool = False,
) -> list[dict[str, Any]]:
    """
    first~last 페이지를 PDF_PART_PAGES 단위로 Upstage 에 보내 element 목록을 반환한다.
    element["page"] 는 원본 PDF 기준 페이지로 보정한다.
    """
    UPSTAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    elements: list[dict[str, Any]] = []

    for start in range(first, last + 1, PDF_PART_PAGES):
        end = min(start + PDF_PART_PAGES - 1, last)
        cache_path = UPSTAGE_CACHE_DIR / f"{pdf_path.stem}_p{start}-{end}.json"

        if cache_path.exists() and not force:
            logger.info("[PDF] Upstage 원본 캐시 사용 | %s", cache_path.name)
            result = json.loads(cache_path.read_text(encoding="utf-8"))
        else:
            logger.info("[PDF] Upstage 호출 | %s p%d-%d", pdf_path.name, start, end)
            part = _cut_pdf(pdf_path, start, end)
            try:
                result = _call_upstage(part)
            finally:
                part.unlink(missing_ok=True)
            for element in result.get("elements", []):
                element["original_page"] = element["page"] + start - 1
            cache_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info(
                "[PDF] Upstage 원본 저장 | %s | elements=%d",
                cache_path.name,
                len(result.get("elements", [])),
            )

        for element in result.get("elements", []):
            element = dict(element)
            element["page"] = element.get("original_page", element["page"] + start - 1)
            elements.append(element)

    return elements


# =========================================================
# 쪽머리 / 목차 / 제목 판정
# =========================================================

SENTENCE_END = re.compile(r"(다\.?|[함음됨임]\.?|\.)$")
# 조항 목록에서 본문 항목이 흔히 끝나는 말 ("~하지 않는 자", "~하는 경우", "~반드시 충족")
BODY_ENDING = re.compile(r"(자|경우|충족|필수|가능|불가)\)?$")
# 번호/기호로 시작하는 줄: 가) (1) 1. ① 제N조 ■
NUMBERED = re.compile(r"^([가-하]\)|\(\d+\)|\d+\.|[①-⑳➀-➉]|제\s*\d+\s*[장조]|[■▶●□])")
KOREAN_ORDER = "가나다라마바사아자차카타파하"


def element_text(element: dict[str, Any]) -> str:
    content = element.get("content") or {}
    text = (
        content.get("text")
        or content.get("markdown")
        or content.get("html")
        or ""
    ).strip()
    return clean_revision_dates(html.unescape(remove_html(text)))


def noise_key(text: str) -> str:
    """반복 비교용 키: 공백 제거, 숫자는 # 로 (쪽번호 "- 12 -" → "-#-")."""
    return re.sub(r"\d+", "#", re.sub(r"\s+", "", text))


def in_page_margin(element: dict[str, Any]) -> bool:
    ys = [point["y"] for point in element.get("coordinates") or [] if "y" in point]
    if not ys:
        return False
    return min(ys) <= MARGIN_TOP or max(ys) >= MARGIN_BOTTOM


def find_repeated_noise(elements: list[dict[str, Any]]) -> set[str]:
    """페이지 위·아래 여백에서 REPEAT_MIN_PAGES 쪽 이상 반복되는 텍스트 키."""
    pages_by_key: dict[str, set[int]] = collections.defaultdict(set)
    for element in elements:
        text = element_text(element)
        if text and len(text) <= MAX_TITLE_LEN and in_page_margin(element):
            pages_by_key[noise_key(text)].add(element["page"])
    return {key for key, pages in pages_by_key.items() if len(pages) >= REPEAT_MIN_PAGES}


def is_page_noise(element: dict[str, Any], text: str, repeated: set[str]) -> bool:
    if element["category"] in NOISE_CATEGORIES:
        return True
    key = noise_key(text)
    if key in PAGE_NOISE_BLACKLIST:
        return True
    return key in repeated and in_page_margin(element)


# 한 글자씩 띄어 쓴 제목("부 전 공", "(4) 제 적")을 붙여 씀. 다음절 단어("수강신청 학점 이월제도")는 그대로
SPACED = re.compile(r"(?<![가-힣])([가-힣])((?: [가-힣])+)(?![가-힣])")


def normalize_title(title: str) -> str:
    return SPACED.sub(lambda m: (m.group(1) + m.group(2)).replace(" ", ""), title)


def is_toc(element: dict[str, Any], text: str) -> bool:
    return element["category"] in TOC_CATEGORIES or text.count("·") >= TOC_DOT_MIN


def heading_level(text: str) -> int:
    """제목 레벨: 번호 없는 제목·제N장 1 > (n)·n.·제N조 2 > 가) 3 > ① 4."""
    if re.match(r"^[①-⑳➀-➉]", text):
        return 4
    if re.match(r"^[가-하]\)", text):
        return 3
    if re.match(r"^(\(\d+\)|\d+\.|제\s*\d+\s*조)", text):
        return 2
    return 1


def item_number(text: str) -> int | None:
    """번호 항목의 순번: (3)→3, 3.→3, 다)→3, ③→3."""
    match = re.match(r"^\((\d+)\)|^(\d+)\.", text)
    if match:
        return int(match.group(1) or match.group(2))
    match = re.match(r"^([가-하])\)", text)
    if match and match.group(1) in KOREAN_ORDER:
        return KOREAN_ORDER.index(match.group(1)) + 1
    if text[:1] and "①" <= text[0] <= "⑳":
        return ord(text[0]) - ord("①") + 1
    if text[:1] and "➀" <= text[0] <= "➉":
        return ord(text[0]) - ord("➀") + 1
    return None


def hangul_ratio(text: str) -> float:
    chars = re.sub(r"\s+", "", text)
    if not chars:
        return 0.0
    return len(re.findall(r"[가-힣]", chars)) / len(chars)


def is_title(text: str, category: str) -> bool:
    text = text.strip()
    if not text or len(text) >= MAX_TITLE_LEN or "\n" in text:
        return False
    if category in BODY_CATEGORIES:
        return False
    if re.match(r"^[*※\-]", text):              # *, ※, - 로 시작하는 주석·안내
        return False
    if re.fullmatch(r"[\d\s]+", text):            # 2021 1 0001
        return False
    if hangul_ratio(text) < MIN_HANGUL_RATIO:     # 기호·영문·숫자 위주
        return False
    if SENTENCE_END.search(text):                  # ~다. / ~함 / ~음 / ~됨 / ~임
        return False
    if BODY_ENDING.search(text):                   # ~하는 자 / ~하는 경우 / ~필수
        return False
    if ":" in text or "→" in text:                # "항목 : 값", "학적 → 부전공신청"
        return False
    if not NUMBERED.match(text) and len(text) > MAX_UNNUMBERED_TITLE_LEN:
        return False                               # 번호 없는 긴 줄은 본문 한 줄로 봄
    return True


# =========================================================
# 청크 생성
# =========================================================

def extract_pdf(
    pdf_path: str | Path,
    school_id: str,
    *,
    pages: tuple[int, int] | None = None,
    skip_pages: set[int] | frozenset[int] = DEFAULT_SKIP_PAGES,
    force: bool = False,
    show_titles: bool = False,
) -> list[dict[str, Any]]:
    """
    PDF 를 Upstage 로 파싱해 RAG 청크 목록을 반환한다.

    pages: (첫 페이지, 마지막 페이지), None 이면 전체
    skip_pages: 버릴 페이지 (표지 등)
    force: 원본 캐시가 있어도 Upstage 재호출
    show_titles: 제목 판정 과정과 제목 띄어쓰기 정규화 전/후 diff 를 로그로 출력
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise PdfExtractionError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")

    total_pages = len(PdfReader(str(pdf_path)).pages)
    first, last = pages or (1, total_pages)
    last = min(last, total_pages)

    elements = load_elements(pdf_path, first, last, force=force)
    repeated = find_repeated_noise(elements)

    doc_name = pdf_path.name
    doc_id = build_doc_id(doc_name, school_id)

    results: list[dict[str, Any]] = []
    stats: collections.Counter[str] = collections.Counter()

    current_chapter: int | None = None
    current_chapter_title: str | None = None

    # 제목 경로: [(레벨, 제목), ...]
    heading_stack: list[tuple[int, str]] = []
    # 레벨별 마지막 번호 항목: level → (순번, 그 항목의 상위 경로)
    # "(12) → 강의시간표 예시 → (13)" 처럼 번호가 이어지면 사이에 낀 번호 없는 제목은 섹션이 아니라고 봄
    last_numbered: dict[int, tuple[int, tuple]] = {}
    # 아직 본문이 붙지 않은 제목이 있는지 (있으면 다음 본문들을 묶어서 내보냄)
    title_waiting = False
    # 경로 마지막 제목이 나온 페이지 (본문 없이 경로만 청크로 남길 때 사용)
    leaf_title_page: int | None = None
    pending_bodies: list[dict[str, Any]] = []
    # 정규화로 바뀐 제목 (원문, 정규화) — show_titles 일 때 diff 출력용
    normalized_pairs: list[tuple[str, str]] = []

    def remember_number(level: int, text: str) -> None:
        # 번호 없는 제목은 기록을 지우지 않음 (끼어든 그림 설명 등을 건너뛰어 번호를 이어 보기 위해)
        number = item_number(text)
        if number is None:
            return
        for deeper in [lv for lv in last_numbered if lv > level]:
            del last_numbered[deeper]
        last_numbered[level] = (number, tuple(e for e in heading_stack if e[0] < level))

    def heading_path() -> str:
        return " > ".join(title for _, title in heading_stack)

    def make_record(text: str, element: dict[str, Any], is_table=False, headers=None, summary=None) -> dict[str, Any]:
        return {
            "text": text,
            "page": element["page"],
            "doc_id": doc_id,
            "doc_name": doc_name,
            "school_id": school_id,
            "chapter": current_chapter,
            "chapter_title": current_chapter_title,
            "article": None,          # 지금은 조 번호를 채우지 않음
            "article_title": None,    # 제목 경로가 있으면 emit() 에서 마지막 제목으로 채움
            "is_table": is_table,
            "table_headers": headers,
            "table_summary": summary,
        }

    def emit(record: dict[str, Any]) -> None:
        """청크 앞에 제목 경로를 붙여 저장 (긴 청크는 나눈 뒤 조각마다 붙임)."""
        path = heading_path()
        if heading_stack and noise_key(record["text"]) == noise_key(heading_stack[-1][1]):
            stats["제목과 같은 본문(버림)"] += 1   # 간지의 "학 사" 등
            return
        for piece in split_long_record(record):
            if path:
                piece["text"] = f"[{path}]\n{piece['text']}"
                piece["article_title"] = heading_stack[-1][1]
            results.append(piece)

    def flush() -> None:
        """제목 뒤에 모아 둔 본문을 하나의 청크로 내보낸다."""
        nonlocal pending_bodies, title_waiting
        if pending_bodies:
            record = dict(pending_bodies[0])
            record["text"] = "\n".join(item["text"] for item in pending_bodies)
            # 표가 섞여 있으면 표 정보를 유지
            for item in pending_bodies:
                if item["is_table"]:
                    record.update(is_table=True, table_headers=item["table_headers"], table_summary=item["table_summary"])
                    break
            emit(record)
            stats["제목-본문 병합"] += 1
            title_waiting = False
        pending_bodies = []

    def next_category(index: int) -> str | None:
        """index 다음의 (쪽머리가 아닌) 요소 category."""
        for following in elements[index + 1:]:
            following_text = element_text(following)
            if following["category"] in CAPTION_TARGETS:
                return following["category"]
            if following_text and not is_page_noise(following, following_text, repeated):
                return following["category"]
        return None

    for index, element in enumerate(elements):
        category = element["category"]
        if category in SKIP_CATEGORIES:
            continue
        if element["page"] in skip_pages:
            stats["표지 제거"] += 1
            continue

        text = element_text(element)
        if not text:
            continue

        if is_page_noise(element, text, repeated):
            stats["쪽머리/쪽번호 제거"] += 1
            continue
        if is_toc(element, text):
            stats["목차 제거"] += 1
            continue

        chapter, chapter_title = extract_chapter(text)
        if chapter is not None:
            current_chapter, current_chapter_title = chapter, chapter_title

        # -----------------------------
        # 제목: 경로(스택) 갱신
        # -----------------------------
        is_caption = not NUMBERED.match(text) and next_category(index) in CAPTION_TARGETS
        if is_caption:
            stats["그림/표 설명(제목 아님)"] += 1
        if is_title(text, category) and not is_caption:
            stats["제목"] += 1
            if show_titles:
                logger.info("[PDF] 제목 p%-4s %-10s %s", element["page"], category, text)
            flush()
            level = heading_level(text)
            if title_waiting and heading_stack and heading_stack[-1][0] >= level:
                # 본문 없이 다음 제목에 밀려나는 제목
                # 번호 있는 항목("다) 과목번호를 직접 입력하여 신청")은 경로만으로 청크를 남기고,
                # 번호 없는 구분 제목("학 사", "학사에 관한 안내")은 버림
                waiting_title = heading_stack[-1][1]
                if NUMBERED.match(waiting_title):
                    results.append({**make_record("", element), "page": leaf_title_page,
                                    "text": f"[{heading_path()}]", "article_title": waiting_title})
                    stats["본문 없는 번호 제목(경로만 청크)"] += 1
                else:
                    stats["본문 없는 구분 제목(버림)"] += 1
                    if show_titles:
                        logger.info("[PDF]   (본문 없음, 버림) %s", waiting_title)
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()

            number = item_number(text)
            previous = last_numbered.get(level)
            if number and previous and previous[0] == number - 1 and tuple(heading_stack) != previous[1]:
                stats["번호 연속으로 경로 복원"] += 1
                if show_titles:
                    logger.info(
                        "[PDF]   (경로 복원) %s → %s",
                        heading_path(),
                        " > ".join(t for _, t in previous[1]),
                    )
                heading_stack = list(previous[1])

            remember_number(level, text)
            title = normalize_title(text)
            if title != text:
                stats["제목 띄어쓰기 정규화"] += 1
                if (text, title) not in normalized_pairs:
                    normalized_pairs.append((text, title))
            heading_stack.append((level, title))
            leaf_title_page = element["page"]
            title_waiting = True
            continue

        # -----------------------------
        # 본문
        # -----------------------------
        if NUMBERED.match(text):
            # "(5) …" 같은 번호 본문은 같은 레벨 이하 제목의 범위를 끝냄
            level = heading_level(text)
            if any(lv >= level for lv, _ in heading_stack):
                flush()
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
            remember_number(level, text)

        if category == "table":
            content = element.get("content") or {}
            table_data = html_table_to_text(content.get("html", ""))
            record = make_record(
                table_data["text"] or remove_html(content.get("html", "")),
                element,
                is_table=True,
                headers=table_data["headers"],
                summary=table_data["rows_summary"],
            )
        else:
            record = make_record(text, element)

        if title_waiting:
            pending_bodies.append(record)
            body_len = sum(len(item["text"]) for item in pending_bodies)
            if record["is_table"] or body_len >= MERGE_MIN_LEN or len(pending_bodies) >= MERGE_MAX_BODIES:
                flush()
            continue

        emit(record)

    flush()
    if title_waiting and heading_stack:
        # 문서 끝에 본문 없이 남은 제목은 경로만으로 내보냄
        last_title = heading_stack[-1]
        results.append({**make_record("", elements[-1]), "page": leaf_title_page,
                        "text": f"[{heading_path()}]", "article_title": last_title[1]})
        stats["문서 끝에 남은 제목"] += 1

    avg_len = sum(len(r["text"]) for r in results) / len(results) if results else 0
    logger.info(
        "[PDF] 추출 완료 | %s p%d-%d | chunks=%d | 평균 %.1f자",
        doc_name,
        first,
        last,
        len(results),
        avg_len,
    )
    logger.info("[PDF] 반복 쪽머리로 판정된 텍스트: %s", sorted(repeated))
    for key, value in stats.items():
        logger.info("[PDF]   %s: %d", key, value)
    if show_titles:
        logger.info("[PDF] 제목 정규화 diff (%d종)", len(normalized_pairs))
        for before, after in normalized_pairs:
            logger.info("[PDF]   - %s", before)
            logger.info("[PDF]   + %s", after)

    return results


def save_chunks(chunks: list[dict[str, Any]], out_path: str | Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("[PDF] 청크 저장 | %s | %d개", out_path, len(chunks))
    return out_path


# =========================================================
# 명령줄 실행
# =========================================================

# 인자 없이 실행했을 때 (예: 에디터의 실행 버튼)
DEFAULT_PDF = BACKEND_DIR / "data" / "raw" / "guide.pdf"
DEFAULT_SCHOOL_ID = "konkuk"


def main() -> None:
    parser = argparse.ArgumentParser(description="PDF → RAG 청크 (Upstage)")
    parser.add_argument("pdf", type=Path, nargs="?", default=DEFAULT_PDF,
                        help=f"PDF 경로 (기본: {DEFAULT_PDF.relative_to(BACKEND_DIR)})")
    parser.add_argument("--school-id", default=DEFAULT_SCHOOL_ID, help=f"학교 ID (기본: {DEFAULT_SCHOOL_ID})")
    parser.add_argument("--pages", default=None, help="처리할 페이지 범위 (예: 1-24, 기본: 전체)")
    parser.add_argument("--out", type=Path, default=None,
                        help="출력 경로 (기본: data/processed/<school_id>/extracted_exp.json)")
    parser.add_argument("--force", action="store_true", help="원본 캐시가 있어도 Upstage 재호출")
    parser.add_argument("--show-titles", action="store_true", help="제목 판정 과정 출력")
    parser.add_argument("--skip-pages", default="1",
                        help="버릴 페이지 (표지 등, 쉼표 구분, 기본: 1). 없으면 빈 문자열")
    args = parser.parse_args()

    pages = tuple(int(x) for x in args.pages.split("-")) if args.pages else None
    skip_pages = {int(x) for x in args.skip_pages.split(",") if x.strip()}
    school_id = args.school_id.strip()

    chunks = extract_pdf(
        args.pdf,
        school_id,
        pages=pages,
        skip_pages=skip_pages,
        force=args.force,
        show_titles=args.show_titles,
    )
    out_path = args.out or BACKEND_DIR / "data" / "processed" / school_id / "extracted_exp.json"
    save_chunks(chunks, out_path)


if __name__ == "__main__":
    main()