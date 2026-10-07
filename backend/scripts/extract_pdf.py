"""
01_extract_pdf.py
Uni-Bot 프로젝트 — 신예진 담당 (OCR/Infra)

PDF 파일에서 페이지별 텍스트를 추출하여
RAG 파이프라인에서 사용할 JSON으로 변환합니다.

출력 예시

{
    "text": "...",
    "page": 3,
    "doc_id": "konkuk-regulation",
    "doc_name": "건국대학교_학칙.pdf",
    "chapter": 9,
    "chapter_title": "휴학·복학·제적 및 자퇴",
    "article": 51,
    "article_title": "휴학",
    "is_table": false
}
"""

import json
import os
import re
import sys
import requests
from pypdf import PdfReader, PdfWriter
import tempfile
import time

from dotenv import load_dotenv

from table_parser import html_table_to_text

# json파일 저장 위치 지정
# 기본 경로 설정
# school_id는 main()에서 명령어 인자를 읽은 뒤에 결정된다.
BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

MAX_CHUNK_LEN = 1800


# .env 파일 읽기 (backend/.env)
load_dotenv(os.path.join(BASE_DIR, "..", ".env"))

# API Key 읽기
API_KEY = os.getenv("UPSTAGE_API_KEY")

if not API_KEY:
    print("UPSTAGE_API_KEY가 설정되지 않았습니다.", file=sys.stderr)
    sys.exit(1)
print("API KEY starts with:", API_KEY[:10])

def clean_revision_dates(text: str) -> str:
    """
    개정일 제거

    제거 예시
    <2024.03.01 개정>
    <개정 2023.02.01>
    (2024.03.01)
    (일부개정 2024.01.01)
    """

    patterns = [
        r"<[^>]*(개정|시행|제정|폐지|공포)[^>]*>",
        r"<\d{4}\.\d{1,2}\.\d{1,2}[^>]*>",
        r"\(\d{4}\.\d{1,2}\.\d{1,2}[^)]*\)",
    ]

    for pattern in patterns:
        text = re.sub(pattern, "", text)

    return text.strip()

def remove_html(text: str) -> str:
    """
    HTML 태그 제거
    <p>안녕하세요</p> -> 안녕하세요
    """

    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()

def extract_chapter(text: str):
    """
    제9장 휴학·복학·제적 및 자퇴

    return
    -------
    (9, "휴학·복학·제적 및 자퇴")
    """

    pattern = r"제\s*(\d+)\s*장\s*\n?\s*(.+)"

    match = re.search(pattern, text)

    if not match:
        return None, None

    chapter_num = int(match.group(1))
    chapter_title = match.group(2).split("\n")[0].strip()

    return chapter_num, chapter_title


def extract_article(text: str):
    """
    제51조(휴학)

    return

    51
    휴학
    """

    pattern = r"제\s*(\d+)\s*조(?:\s*\((.*?)\))?"

    match = re.search(pattern, text)

    if match:
        title = match.group(2) or ""
        return int(match.group(1)), title.strip()

    # 제목 없는 조
    pattern = r"제\s*(\d+)\s*조"

    match = re.search(pattern, text)

    if match:
        return int(match.group(1)), ""

    return None, None

def is_title(text: str) -> bool:
    if len(text) >= 40:
        return False

    patterns = [
        r"^[가-힣]\)\s*",       # 가) 나)
        r"^\(\d+\)\s*",         # (1) (2)
        r"^\d+\.\s*",           # 1. 2.
        r"^제\s*\d+\s*조",      # 제N조
        r"^[■▶●]\s*",           # ■ ▶ ●
    ]

    return any(re.match(pattern, text) for pattern in patterns)

def split_long_record(record):
    text = record["text"]

    if len(text) <= MAX_CHUNK_LEN:
        return [record]

    sentences = re.split(r"(?<=[.!?。！？])\s*", text)

    chunks = []
    current_text = ""

    for sentence in sentences:
        if not sentence:
            continue

        # 문장 하나가 MAX_CHUNK_LEN보다 긴 경우
        if len(sentence) > MAX_CHUNK_LEN:
            if current_text:
                new_record = record.copy()
                new_record["text"] = current_text.strip()
                chunks.append(new_record)
                current_text = ""

            for i in range(0, len(sentence), MAX_CHUNK_LEN):
                new_record = record.copy()
                new_record["text"] = sentence[i:i + MAX_CHUNK_LEN].strip()
                chunks.append(new_record)

            continue

        if current_text and len(current_text) + len(sentence) + 1 > MAX_CHUNK_LEN:
            new_record = record.copy()
            new_record["text"] = current_text.strip()
            chunks.append(new_record)
            current_text = sentence
        else:
            if current_text:
                current_text += " "
            current_text += sentence

    if current_text.strip():
        new_record = record.copy()
        new_record["text"] = current_text.strip()
        chunks.append(new_record)

    return chunks

def build_doc_id(
    filename: str,
    school_id: str,
) -> str:
    """
    파일명과 학교 식별자로 문서 ID를 생성합니다.

    예:
    school_id = "konkuk"
    filename = "guide.pdf"

    결과:
    konkuk-guide
    """
    name = os.path.splitext(filename)[0]

    filename_slug = (
        name.lower()
        .replace(" ", "-")
        .replace("_", "-")
    )

    return f"{school_id}-{filename_slug}"

def parse_pdf_with_upstage(pdf_path: str):

    url = "https://api.upstage.ai/v1/document-ai/document-parse"

    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }

    data = {
        "ocr": "auto"
    }

    with open(pdf_path, "rb") as f:

        files = {
            "document": f
        }

        response = requests.post(
            url,
            headers=headers,
            files=files,
            data=data,
            timeout=300

        )

    response.raise_for_status()

    result = response.json()

    print(f"parsed elements: {len(result['elements'])}", file=sys.stderr)

    return result

def split_pdf(pdf_path, chunk_size=100):
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)

    chunks = []

    for start in range(0, total_pages, chunk_size):
        writer = PdfWriter()
        end = min(start + chunk_size, total_pages)

        for i in range(start, end):
            writer.add_page(reader.pages[i])

        temp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        writer.write(temp)
        temp.close()

        chunks.append((temp.name, start))

    return chunks


def extract_pdf(
    pdf_path: str,
    school_id: str,
):

    response = parse_pdf_with_upstage(pdf_path)

    doc_name = os.path.basename(pdf_path)
    doc_id = build_doc_id(
        doc_name,
        school_id,
    )

    results = []
    seen_pages = set()

    pending_record = None
    pending_count = 0
    merge_count = 0
    title_count = 0


    # 현재 장/조 정보 유지
    current_chapter = None
    current_chapter_title = None

    current_article = None
    current_article_title = None

    for element in response["elements"]:

        page_num = element["page"]
        category = element["category"]

        if category in ["figure", "image"]:
            continue

        try:
            content = element["content"]

            text = (
                content.get("text")
                or content.get("markdown")
                or content.get("html")
                or ""
            ).strip()

            text = remove_html(text)

        except Exception as e:

            print(f"element 처리 완료 (page {page_num})", file=sys.stderr)

            text = ""

        # -----------------------------
        # 개정일 제거
        # -----------------------------

        text = clean_revision_dates(text)
        
        if not text:
            continue

        # -----------------------------
        # 장 정보 추출
        # -----------------------------

        chapter, chapter_title = extract_chapter(text)

        if chapter is not None:
            current_chapter = chapter
            current_chapter_title = chapter_title

        # -----------------------------
        # 조 정보 추출
        # -----------------------------

        article, article_title = extract_article(text)

        if article is not None:
            current_article = article
            current_article_title = article_title

        # -----------------------------
        # 표 여부
        # Upstage가 반환한 <table> HTML을
        # table_parser.html_table_to_text로 자연어 문장 변환
        # -----------------------------

        is_table = element["category"] == "table"

        table_headers = None
        table_summary = None

        if is_table:
            table_html = content.get("html", "")
            table_data = html_table_to_text(table_html)
            text = table_data["text"] or remove_html(table_html)
            table_headers = table_data["headers"]
            table_summary = table_data["rows_summary"]

        # -----------------------------
        # JSON 생성
        # -----------------------------

        record = {

            "text": text,

            "page": page_num,

            "doc_id": doc_id,

            "doc_name": doc_name,

            "school_id": school_id,

            "chapter": current_chapter,

            "chapter_title": current_chapter_title,

            "article": current_article,

            "article_title": current_article_title,

            "is_table": is_table,

            "table_headers": table_headers,

            "table_summary": table_summary,
        }

        if is_title(text):
            if pending_record is not None:
                results.extend(split_long_record(pending_record))
                pending_record = None
                pending_count = 0

            record["article_title"] = text
            pending_record = record
            pending_count = 1
            title_count += 1
            continue

        if pending_record is not None:
            pending_record["text"] += "\n" + text
            pending_count += 1
            merge_count += 1

            if (
                len(pending_record["text"]) >= 100
                or pending_count >= 3
            ):
                results.extend(split_long_record(pending_record))
                pending_record = None
                pending_count = 0

            continue

        results.extend(split_long_record(record))


        if page_num not in seen_pages:
            print(
                f"page {page_num} 처리 완료",
                file=sys.stderr
            )
            seen_pages.add(page_num)

    if pending_record is not None:
        results.extend(split_long_record(pending_record))
        pending_record = None
        pending_count = 0

    total_chunks = len(results)

    article_title_count = sum(
        1 for record in results
        if record.get("article_title")
    )

    avg_chunk_length = (
        sum(len(record["text"]) for record in results) / total_chunks
        if total_chunks > 0
        else 0
    )

    article_title_fill_rate = (
        article_title_count / total_chunks * 100
        if total_chunks > 0
        else 0
    )

    print(
        f"\n완료! 총 {total_chunks}개 chunk",
        file=sys.stderr
    )

    print(
        f"제목-본문 병합 횟수: {merge_count}",
        file=sys.stderr
    )

    print(
        f"article_title 채움률: {article_title_fill_rate:.2f}%",
        file=sys.stderr
    )

    print(
        f"평균 chunk 길이: {avg_chunk_length:.2f}자",
        file=sys.stderr
    )

    return results

def main():

    # -----------------------------
    # 인자 확인
    # -----------------------------

    if len(sys.argv) < 4:
        print(
            "사용법:",
            file=sys.stderr,
        )

        print(
            (
                "python 01_extract_pdf.py "
                "<pdf파일> --school-id <학교ID>"
            ),
            file=sys.stderr,
        )

        print(
            "예시:",
            file=sys.stderr,
        )

        print(
            (
                "python 01_extract_pdf.py "
                "data/학칙.pdf --school-id konkuk"
            ),
            file=sys.stderr,
        )

        sys.exit(1)

    pdf_path = sys.argv[1]

    if sys.argv[2] != "--school-id":
        print(
            "--school-id 옵션이 필요합니다.",
            file=sys.stderr,
        )
        sys.exit(1)

    school_id = sys.argv[3].strip()

    if not school_id:
        print(
            "school_id 값이 비어 있습니다.",
            file=sys.stderr,
        )
        sys.exit(1)

    school_output_dir = os.path.join(
        BASE_DIR,
        "..",
        "data",
        "processed",
        school_id,
    )

    os.makedirs(
        school_output_dir,
        exist_ok=True,
    )

    school_output_path = os.path.join(
        school_output_dir,
        "extracted.json",
    )    

    all_pages = []

    chunks = split_pdf(pdf_path, 50)

    for i, (chunk, start_page) in enumerate(chunks):
        print(f"{i+1}/{len(chunks)} 번째 PDF 처리 중...", file=sys.stderr)

        pages = extract_pdf(
            chunk,
            school_id,
        )

        for p in pages:
            p["page"] += start_page  # ⭐ chunk 기준 보정

        all_pages.extend(pages)

    with open(
        school_output_path,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            all_pages,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(f"저장 완료: {school_output_path}")


if __name__ == "__main__":
    main()
