"""
20개 표준 질의 체크리스트 검수 스크립트.

※ 현재는 article 자동 판정을 끄고, 사람이 Top-N 페이지/문장을
  직접 보고 verdict를 채우기 위한 임시 모드입니다. (삭제 예정)

사용법 (backend 디렉터리에서):
    python scripts/check_questions.py
    python scripts/check_questions.py --school-id konkuk
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.rag_service import search

CHECKLIST_PATH = BACKEND_DIR / "evaluation" / "questions_checklist.csv"
# 자동 판정 결과용 (기존). 현재 임시 검수 모드에서는 쓰지 않음.
RESULT_PATH = BACKEND_DIR / "evaluation" / "checklist_result.csv"
# [삭제 예정] 사람 검수용 출력
REVIEW_PATH = BACKEND_DIR / "evaluation" / "checklist_review.csv"

DEFAULT_SCHOOL_ID = "konkuk"
TOP_N = 3
# [삭제 예정] 콘솔/CSV에 보여줄 본문 최대 길이
TEXT_PREVIEW_LEN = 180

VARIANT_LABELS = {
    "A": "완전문장",
    "B": "구어체",
    "C": "키워드형",
}


@dataclass
class ChecklistRow:
    id: str
    category: str
    variant: str
    question: str
    expected_article: str
    expected_page: str
    must_pass: bool


@dataclass
class HitPreview:
    rank: int
    page: str
    score: str
    article: str
    text: str


@dataclass
class EvalResult:
    id: str
    variant: str
    question: str
    expected_article: str
    expected_page: str
    # 사람이 채울 칸 — 자동 판정 OFF 상태에서는 비워 둔다.
    verdict: str
    top1_article: str
    top1_score: str
    rank_of_expected: str
    must_pass: bool
    # [삭제 예정] 사람 검수용 Top-N 미리보기
    hits: list[HitPreview] = field(default_factory=list)


def parse_bool(value: str) -> bool:
    return str(value).strip().upper() in {"TRUE", "1", "YES", "Y"}


def normalize_article(value: object) -> str:
    return str(value or "").strip()


def clean_preview_text(text: object, max_len: int = TEXT_PREVIEW_LEN) -> str:
    """사람이 읽기 좋게 공백을 정리하고 길이를 자른다. [삭제 예정]"""
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[:max_len].rstrip() + "…"


# ---------------------------------------------------------------------------
# [일시 비활성] article / article_title 자동 일치 판정
# JSON(메타데이터)의 article 값이 기대값과 형식이 달라
# 자동 PASS/PARTIAL/FAIL이 신뢰하기 어려워 잠시 주석 처리함.
# ---------------------------------------------------------------------------
#
# def article_matches(result: dict, expected_article: str) -> bool:
#     """검색 결과의 article / article_title이 expected_article과 일치하는지 판정."""
#     expected = normalize_article(expected_article)
#     if not expected:
#         return False
#
#     candidates = [
#         normalize_article(result.get("article")),
#         normalize_article(result.get("article_title")),
#     ]
#
#     for candidate in candidates:
#         if not candidate:
#             continue
#         if (
#             candidate == expected
#             or expected in candidate
#             or candidate in expected
#         ):
#             return True
#
#     return False
#
#
# def find_expected_rank(
#     results: list[dict],
#     expected_article: str,
# ) -> int | None:
#     for rank, result in enumerate(results, start=1):
#         if article_matches(result, expected_article):
#             return rank
#     return None


def load_checklist(path: Path) -> list[ChecklistRow]:
    if not path.exists():
        raise FileNotFoundError(f"체크리스트 CSV를 찾을 수 없습니다: {path}")

    rows: list[ChecklistRow] = []

    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        required = {
            "id",
            "category",
            "variant",
            "question",
            "expected_article",
            "expected_page",
            "must_pass",
        }
        if reader.fieldnames is None or not required.issubset(
            set(reader.fieldnames)
        ):
            raise ValueError(
                "체크리스트 CSV 컬럼이 올바르지 않습니다. "
                f"필요 컬럼: {sorted(required)}"
            )

        for raw in reader:
            question = (raw.get("question") or "").strip()
            if not question:
                continue

            rows.append(
                ChecklistRow(
                    id=(raw.get("id") or "").strip(),
                    category=(raw.get("category") or "").strip(),
                    variant=(raw.get("variant") or "").strip().upper(),
                    question=question,
                    expected_article=(
                        raw.get("expected_article") or ""
                    ).strip(),
                    expected_page=(raw.get("expected_page") or "").strip(),
                    must_pass=parse_bool(raw.get("must_pass") or ""),
                )
            )

    if not rows:
        raise ValueError("체크리스트에 유효한 질문이 없습니다.")

    return rows


def build_hits(results: list[dict]) -> list[HitPreview]:
    """[삭제 예정] Top-N 검색 결과를 검수용 미리보기로 변환."""
    hits: list[HitPreview] = []

    for rank, result in enumerate(results, start=1):
        page = str(result.get("page") or "").strip()
        article = normalize_article(
            result.get("article") or result.get("article_title")
        )
        score = f"{float(result.get('score') or 0.0):.4f}"
        text = clean_preview_text(result.get("text"))
        hits.append(
            HitPreview(
                rank=rank,
                page=page,
                score=score,
                article=article,
                text=text,
            )
        )

    return hits


def evaluate_row(
    row: ChecklistRow,
    *,
    school_id: str,
) -> EvalResult:
    top_n = search(
        row.question,
        n_results=TOP_N,
        school_id=school_id,
    )

    if not top_n:
        return EvalResult(
            id=row.id,
            variant=row.variant,
            question=row.question,
            expected_article=row.expected_article,
            expected_page=row.expected_page,
            verdict="",  # 사람 검수란
            top1_article="",
            top1_score="",
            rank_of_expected="",
            must_pass=row.must_pass,
            hits=[],
        )

    hits = build_hits(top_n)
    top1 = hits[0]

    # ------------------------------------------------------------------
    # [일시 비활성] article 일치 기반 자동 판정
    # ------------------------------------------------------------------
    # rank_in_top3 = find_expected_rank(top_n, row.expected_article)
    # if rank_in_top3 is not None:
    #     verdict = "PASS"
    #     rank_of_expected = str(rank_in_top3)
    # else:
    #     top10 = search(
    #         row.question,
    #         n_results=TOP_K_PARTIAL,
    #         school_id=school_id,
    #     )
    #     rank_in_top10 = find_expected_rank(top10, row.expected_article)
    #     if rank_in_top10 is not None:
    #         verdict = "PARTIAL"
    #         rank_of_expected = str(rank_in_top10)
    #     else:
    #         verdict = "FAIL"
    #         rank_of_expected = ""
    #
    # return EvalResult(..., verdict=verdict, rank_of_expected=rank_of_expected)

    return EvalResult(
        id=row.id,
        variant=row.variant,
        question=row.question,
        expected_article=row.expected_article,
        expected_page=row.expected_page,
        verdict="",  # 사람이 PASS/PARTIAL/FAIL/EMPTY를 직접 기입
        top1_article=top1.article,
        top1_score=top1.score,
        rank_of_expected="",
        must_pass=row.must_pass,
        hits=hits,
    )


def save_review_csv(path: Path, results: list[EvalResult]) -> None:
    """[삭제 예정] 사람 검수용 CSV 저장."""
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "id",
        "variant",
        "question",
        "expected_article",
        "expected_page",
        "verdict",  # 사람이 채움
        "top1_page",
        "top1_score",
        "top1_text",
        "top2_page",
        "top2_score",
        "top2_text",
        "top3_page",
        "top3_score",
        "top3_text",
    ]

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            row: dict[str, str] = {
                "id": result.id,
                "variant": result.variant,
                "question": result.question,
                "expected_article": result.expected_article,
                "expected_page": result.expected_page,
                "verdict": result.verdict,
                "top1_page": "",
                "top1_score": "",
                "top1_text": "",
                "top2_page": "",
                "top2_score": "",
                "top2_text": "",
                "top3_page": "",
                "top3_score": "",
                "top3_text": "",
            }

            for hit in result.hits:
                prefix = f"top{hit.rank}"
                if prefix + "_page" not in row:
                    continue
                row[f"{prefix}_page"] = hit.page
                row[f"{prefix}_score"] = hit.score
                row[f"{prefix}_text"] = hit.text

            writer.writerow(row)


def print_review_block(result: EvalResult, index: int, total: int) -> None:
    """[삭제 예정] 콘솔에 사람이 읽기 좋은 검수 블록 출력."""
    variant_label = VARIANT_LABELS.get(result.variant, result.variant)

    print()
    print("=" * 72)
    print(
        f"[{index}/{total}] {result.id} / {result.variant} ({variant_label})"
    )
    print(f"질문: {result.question}")
    print(
        f"기대: article={result.expected_article or '-'} "
        f"| page={result.expected_page or '-'}"
    )
    print("-" * 72)

    if not result.hits:
        print("  (검색 결과 없음 → EMPTY 후보)")
        print("  verdict: ________  (PASS / PARTIAL / FAIL / EMPTY)")
        return

    for hit in result.hits:
        print(
            f"  #{hit.rank}  page={hit.page or '-'}  "
            f"score={hit.score}  article={hit.article or '-'}"
        )
        print(f"      {hit.text or '(본문 없음)'}")

    print("-" * 72)
    print("  verdict: ________  (PASS / PARTIAL / FAIL / EMPTY)")


def print_manual_guide(results: list[EvalResult]) -> None:
    empty_count = sum(1 for item in results if not item.hits)
    print()
    print("=" * 72)
    print("[임시 검수 모드] article 자동 판정 OFF")
    print(f"총 {len(results)}건 조회 완료 (검색결과 없음: {empty_count}건)")
    print("verdict는 CSV의 빈 칸에 직접 기입하세요.")
    print("  PASS    : Top-3 안에 기대 내용이 있음")
    print("  PARTIAL : Top-3엔 없지만 관련 내용은 보임 (참고)")
    print("  FAIL    : Top-3가 기대와 무관")
    print("  EMPTY   : 검색 결과 0건")
    print("=" * 72)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "표준 질의 체크리스트 검색 결과를 사람 검수용으로 출력합니다. "
            "(article 자동 판정 일시 비활성)"
        ),
    )
    parser.add_argument(
        "--checklist",
        type=Path,
        default=CHECKLIST_PATH,
        help=f"입력 체크리스트 CSV (기본: {CHECKLIST_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REVIEW_PATH,
        help=f"검수용 CSV 경로 (기본: {REVIEW_PATH})",
    )
    parser.add_argument(
        "--school-id",
        default=DEFAULT_SCHOOL_ID,
        help=f"검색 school_id 필터 (기본: {DEFAULT_SCHOOL_ID})",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="콘솔 상세 검수 블록을 생략하고 요약만 출력",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    checklist_path = (
        args.checklist
        if args.checklist.is_absolute()
        else BACKEND_DIR / args.checklist
    )
    output_path = (
        args.output
        if args.output.is_absolute()
        else BACKEND_DIR / args.output
    )

    try:
        checklist = load_checklist(checklist_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    print(f"체크리스트: {checklist_path}")
    print(f"학교 필터: {args.school_id}")
    print(f"질문 수: {len(checklist)}")
    print("모드: 사람 검수 (article 자동 판정 OFF)")

    results: list[EvalResult] = []

    for index, row in enumerate(checklist, start=1):
        if args.quiet:
            print(
                f"[{index}/{len(checklist)}] "
                f"{row.id}/{row.variant} 검색 중...",
                flush=True,
            )

        result = evaluate_row(row, school_id=args.school_id)
        results.append(result)

        if not args.quiet:
            print_review_block(result, index, len(checklist))

    save_review_csv(output_path, results)
    print(f"\n검수용 CSV 저장: {output_path}")
    print(
        f"(참고) 기존 자동판정 결과 파일은 건드리지 않음: {RESULT_PATH}"
    )
    print_manual_guide(results)

    # 자동 판정 OFF → must_pass FAIL로 CI 종료하지 않음
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
