"""
20개 표준 질의 체크리스트 자동 검증 스크립트.

판정:
  - PASS    : Top-3 안에 expected_article이 포함됨
  - PARTIAL : Top-3에는 없지만 Top-10에는 있음
  - FAIL    : Top-10에도 없음
  - EMPTY   : 검색 결과 0건 (min_score 등으로 전부됨)

사용법 (backend 디렉터리에서):
    python scripts/check_questions.py
    python scripts/check_questions.py --school-id konkuk
    python scripts/check_questions.py --log-output evaluation/my_log.txt
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
RESULT_PATH = BACKEND_DIR / "evaluation" / "checklist_result.csv"
# [삭제 예정] 사람 검수용 Top-10 미리보기
REVIEW_PATH = BACKEND_DIR / "evaluation" / "checklist_review.csv"
LOG_PATH = BACKEND_DIR / "evaluation" / "checklist_console.txt"

DEFAULT_SCHOOL_ID = "konkuk"
TOP_K_PASS = 3
TOP_K_PARTIAL = 10
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
    verdict: str
    top1_article: str
    top1_score: str
    rank_of_expected: str
    must_pass: bool
    # [삭제 예정] 사람 검수용 Top-10 미리보기
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


def article_matches(result: dict, expected_article: str) -> bool:
    """검색 결과의 article / article_title이 expected_article과 일치하는지 판정."""
    expected = normalize_article(expected_article)
    if not expected:
        return False

    candidates = [
        normalize_article(result.get("article")),
        normalize_article(result.get("article_title")),
    ]

    for candidate in candidates:
        if not candidate:
            continue
        if (
            candidate == expected
            or expected in candidate
            or candidate in expected
        ):
            return True

    return False


def find_expected_rank(
    results: list[dict],
    expected_article: str,
) -> int | None:
    for rank, result in enumerate(results, start=1):
        if article_matches(result, expected_article):
            return rank
    return None


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
    """[삭제 예정] 검색 결과를 검수용 미리보기로 변환."""
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
    # Top-3 / Top-10 판정을 같은 순위표에서 하도록 n_results=10으로 한 번 검색
    top10 = search(
        row.question,
        n_results=TOP_K_PARTIAL,
        school_id=school_id,
    )

    if not top10:
        return EvalResult(
            id=row.id,
            variant=row.variant,
            question=row.question,
            expected_article=row.expected_article,
            expected_page=row.expected_page,
            verdict="EMPTY",
            top1_article="",
            top1_score="",
            rank_of_expected="",
            must_pass=row.must_pass,
            hits=[],
        )

    top3 = top10[:TOP_K_PASS]
    hits = build_hits(top10)

    top1 = top3[0]
    top1_article = normalize_article(
        top1.get("article") or top1.get("article_title")
    )
    top1_score = f"{float(top1.get('score') or 0.0):.4f}"

    rank_in_top3 = find_expected_rank(top3, row.expected_article)
    if rank_in_top3 is not None:
        return EvalResult(
            id=row.id,
            variant=row.variant,
            question=row.question,
            expected_article=row.expected_article,
            expected_page=row.expected_page,
            verdict="PASS",
            top1_article=top1_article,
            top1_score=top1_score,
            rank_of_expected=str(rank_in_top3),
            must_pass=row.must_pass,
            hits=hits,
        )

    rank_in_top10 = find_expected_rank(top10, row.expected_article)
    if rank_in_top10 is not None:
        return EvalResult(
            id=row.id,
            variant=row.variant,
            question=row.question,
            expected_article=row.expected_article,
            expected_page=row.expected_page,
            verdict="PARTIAL",
            top1_article=top1_article,
            top1_score=top1_score,
            rank_of_expected=str(rank_in_top10),
            must_pass=row.must_pass,
            hits=hits,
        )

    return EvalResult(
        id=row.id,
        variant=row.variant,
        question=row.question,
        expected_article=row.expected_article,
        expected_page=row.expected_page,
        verdict="FAIL",
        top1_article=top1_article,
        top1_score=top1_score,
        rank_of_expected="",
        must_pass=row.must_pass,
        hits=hits,
    )


def save_results(path: Path, results: list[EvalResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "id",
        "variant",
        "question",
        "verdict",
        "top1_article",
        "top1_score",
        "rank_of_expected",
    ]

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "id": result.id,
                    "variant": result.variant,
                    "question": result.question,
                    "verdict": result.verdict,
                    "top1_article": result.top1_article,
                    "top1_score": result.top1_score,
                    "rank_of_expected": result.rank_of_expected,
                }
            )


def save_review_csv(path: Path, results: list[EvalResult]) -> None:
    """[삭제 예정] 사람 검수용 Top-10 CSV 저장."""
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "id",
        "variant",
        "question",
        "expected_article",
        "expected_page",
        "verdict",
        "rank_of_expected",
    ]
    for rank in range(1, TOP_K_PARTIAL + 1):
        fieldnames.extend(
            [
                f"top{rank}_page",
                f"top{rank}_score",
                f"top{rank}_text",
            ]
        )

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
                "rank_of_expected": result.rank_of_expected,
            }
            for rank in range(1, TOP_K_PARTIAL + 1):
                row[f"top{rank}_page"] = ""
                row[f"top{rank}_score"] = ""
                row[f"top{rank}_text"] = ""

            for hit in result.hits:
                if hit.rank > TOP_K_PARTIAL:
                    continue
                row[f"top{hit.rank}_page"] = hit.page
                row[f"top{hit.rank}_score"] = hit.score
                row[f"top{hit.rank}_text"] = hit.text

            writer.writerow(row)


def print_review_block(result: EvalResult, index: int, total: int) -> None:
    """[삭제 예정] 콘솔에 Top-10 검수 블록 출력."""
    variant_label = VARIANT_LABELS.get(result.variant, result.variant)

    print()
    print("=" * 72)
    print(
        f"[{index}/{total}] {result.id} / {result.variant} ({variant_label}) "
        f"→ {result.verdict}"
    )
    print(f"질문: {result.question}")
    print(
        f"기대: article={result.expected_article or '-'} "
        f"| page={result.expected_page or '-'} "
        f"| rank={result.rank_of_expected or '-'}"
    )
    print("-" * 72)

    if not result.hits:
        print("  (검색 결과 없음 → EMPTY)")
        return

    for hit in result.hits:
        marker = ""
        if hit.rank <= TOP_K_PASS:
            marker = " [Top-3]"
        print(
            f"  #{hit.rank:<2}{marker}  page={hit.page or '-'}  "
            f"score={hit.score}  article={hit.article or '-'}"
        )
        print(f"       {hit.text or '(본문 없음)'}")


def print_summary(results: list[EvalResult]) -> None:
    total = len(results)
    pass_count = sum(1 for item in results if item.verdict == "PASS")
    partial_count = sum(1 for item in results if item.verdict == "PARTIAL")
    fail_count = sum(1 for item in results if item.verdict == "FAIL")
    empty_count = sum(1 for item in results if item.verdict == "EMPTY")
    pass_rate = (pass_count / total * 100.0) if total else 0.0

    print()
    print(
        f"전체 통과율(PASS): {pass_count}/{total} ({pass_rate:.1f}%)"
    )
    print(
        f"판정 분포: PASS={pass_count}  PARTIAL={partial_count}  "
        f"FAIL={fail_count}  EMPTY={empty_count}"
    )
    print()
    print("변형별 통과율(PASS):")

    for variant in ("A", "B", "C"):
        variant_rows = [
            item for item in results if item.variant == variant
        ]
        if not variant_rows:
            continue

        variant_pass = sum(
            1 for item in variant_rows if item.verdict == "PASS"
        )
        variant_total = len(variant_rows)
        variant_rate = (
            variant_pass / variant_total * 100.0
            if variant_total
            else 0.0
        )
        label = VARIANT_LABELS.get(variant, variant)
        print(
            f"  {variant} ({label}): "
            f"{variant_pass}/{variant_total} "
            f"({variant_rate:.1f}%)"
        )

    bad_rows = [
        item
        for item in results
        if item.verdict in {"FAIL", "EMPTY"}
    ]

    print()
    if not bad_rows:
        print("FAIL/EMPTY 목록: 없음")
        return

    print("FAIL/EMPTY 목록:")
    print("| id | variant | question | verdict |")
    print("|---|---|---|---|")
    for item in bad_rows:
        question = item.question.replace("|", "\\|")
        print(
            f"| {item.id} | {item.variant} | {question} | {item.verdict} |"
        )


class TeeWriter:
    """stdout과 로그 파일에 동시에 기록합니다."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, data: str) -> int:
        for stream in self.streams:
            stream.write(data)
            stream.flush()
        return len(data)

    def flush(self) -> None:
        for stream in self.streams:
            stream.flush()

    def isatty(self) -> bool:
        return False


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else BACKEND_DIR / path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "표준 질의 체크리스트를 RAG 검색으로 자동 검증합니다. "
            "(PASS/PARTIAL/FAIL/EMPTY)"
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
        default=RESULT_PATH,
        help=f"자동 판정 결과 CSV (기본: {RESULT_PATH})",
    )
    parser.add_argument(
        "--review-output",
        type=Path,
        default=REVIEW_PATH,
        help=f"Top-10 검수용 CSV (기본: {REVIEW_PATH})",
    )
    parser.add_argument(
        "--log-output",
        type=Path,
        default=LOG_PATH,
        help=f"터미널 출력 저장 txt (기본: {LOG_PATH})",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="터미널 출력 txt 저장을 하지 않음",
    )
    parser.add_argument(
        "--school-id",
        default=DEFAULT_SCHOOL_ID,
        help=f"검색 school_id 필터 (기본: {DEFAULT_SCHOOL_ID})",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="콘솔 Top-10 상세 블록을 생략하고 요약만 출력",
    )
    parser.add_argument(
        "--skip-result",
        action="store_true",
        help="checklist_result.csv 저장을 건너뜀",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    checklist_path = resolve_path(args.checklist)
    output_path = resolve_path(args.output)
    review_path = resolve_path(args.review_output)
    log_path = resolve_path(args.log_output)

    try:
        checklist = load_checklist(checklist_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    original_stdout = sys.stdout
    log_file = None

    if not args.no_log:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_file = log_path.open("w", encoding="utf-8")
        sys.stdout = TeeWriter(original_stdout, log_file)

    try:
        print(f"체크리스트: {checklist_path}")
        print(f"학교 필터: {args.school_id}")
        print(f"질문 수: {len(checklist)}")
        print(
            f"판정: Top-{TOP_K_PASS}=PASS / "
            f"Top-{TOP_K_PARTIAL}=PARTIAL / 밖=FAIL / 0건=EMPTY"
        )
        if log_file is not None:
            print(f"콘솔 로그: {log_path}")

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

            if args.quiet:
                print(
                    f"  → {result.verdict}"
                    f" (top1={result.top1_article or '-'}, "
                    f"score={result.top1_score or '-'}, "
                    f"rank={result.rank_of_expected or '-'})"
                )
            else:
                print_review_block(result, index, len(checklist))

        if not args.skip_result:
            save_results(output_path, results)
            print(f"\n자동 판정 결과 저장: {output_path}")

        save_review_csv(review_path, results)
        print(f"Top-10 검수용 CSV 저장: {review_path}")
        print_summary(results)

        if log_file is not None:
            print(f"\n터미널 출력 저장: {log_path}")

        must_pass_failures = [
            item
            for item in results
            if item.must_pass and item.verdict == "FAIL"
        ]

        if must_pass_failures:
            print()
            print(
                f"must_pass FAIL {len(must_pass_failures)}건 "
                "→ exit code 1",
                file=sys.stderr,
            )
            return 1

        return 0
    finally:
        sys.stdout = original_stdout
        if log_file is not None:
            log_file.close()


if __name__ == "__main__":
    raise SystemExit(main())
