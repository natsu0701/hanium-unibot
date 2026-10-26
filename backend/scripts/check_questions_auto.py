"""
9/7 Top-3 검색 정확도 실험(check_questions.py)을 같은 방식으로 다시 돌리되,
사람이 하던 판정을 정답 키워드 기반 자동 판정으로 바꾼 스크립트.

실험 방식 (9/7 실험과 동일)
  - 질의: evaluation/questions_checklist.csv (20개 표준 질의 × A 완전문장 / B 구어체 / C 키워드형 = 60개)
  - 검색: 운영 rag_service.search() 로 ChromaDB 에서 Top-10 을 한 번에 조회 (school_id 필터)
  - 판정 기준
      PASS    : 질문에 대한 완결된 답이 Top-3 안에 있음
      PARTIAL : 완결된 답이 Top-4~10 안에 있음
      FAIL    : Top-10 전체에 완결된 답이 없음 (제목만 / 키워드만 일치 / 답이 잘림 포함)
      EMPTY   : 검색 결과 0건

자동 판정
  - "완결된 답" = 질문별 정답 키워드(ANSWER_KEYWORDS)가 한 청크 안에 모두 있는 것 (공백 무시)
    답이 두 섹션에 걸친 질문(MULTI_PART_KEYWORDS, 예: Q14 다전공 자격+학점)은 묶음별로 각각 찾아야 완결
    → 제목만 있는 청크, 키워드 일부만 맞는 청크, 답이 잘려 핵심 수치가 빠진 청크는 정답으로 치지 않음
  - 판정에는 미리보기가 아닌 청크 전문을 사용

산출물
    evaluation/auto_checklist_result.csv   질문별 판정
    evaluation/auto_checklist_review.csv   Top-10 검수용 (순위별 페이지·점수·본문, 정답 청크 표시)
    evaluation/auto_checklist_console.txt  터미널 출력

사용법 (backend 디렉터리에서, 백엔드 서버는 꺼 둔 상태 권장):
    .venv/bin/python scripts/check_questions_auto.py
    .venv/bin/python scripts/check_questions_auto.py --quiet
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
for path in (BACKEND_DIR, SCRIPTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.services.rag_service import search  # noqa: E402
from check_questions import (  # noqa: E402
    CHECKLIST_PATH,
    DEFAULT_SCHOOL_ID,
    TOP_K_PARTIAL,
    TOP_K_PASS,
    VARIANT_LABELS,
    ChecklistRow,
    TeeWriter,
    clean_preview_text,
    load_checklist,
    resolve_path,
)

# 질문 id 별 정답 키워드 (한 청크 안에 모두 있어야 정답 청크로 인정, 공백 무시)
ANSWER_KEYWORDS: dict[str, list[str]] = {
    "Q01": ["이월학점", "1~3학점"],                    # 학점이월 범위
    "Q02": ["입대휴학", "가사휴학", "육아휴학"],        # 휴학 종류
    "Q03": ["복학신청", "복학승인", "수강신청"],        # 복학생 수강신청
    "Q04": ["재입학", "여석"],                         # 재입학 가능 여부
    "Q05": ["제적처리", "복학을하지않는자"],            # 제적 사유
    "Q06": ["부전공", "총24학점"],                     # 부전공 이수학점
    "Q07": ["계절학기", "최대6학점"],                   # 계절학기 신청학점
    "Q08": ["계절학기", "16일"],                       # 계절학기 개설기간
    "Q09": ["학사경고", "2.0미만"],                    # 학사경고 기준
    "Q10": ["한도학점", "17학점", "19학점"],            # 수강신청 학점 한도
    "Q11": ["취득학점포기", "C+이하"],                  # 취득학점 포기
    "Q12": ["성적이의신청", "학업성적정정원"],          # 성적 이의신청
    "Q13": ["부전공", "신청자격", "3~8학기"],           # 부전공 신청자격
    "Q14": ["다전공", "신청자격", "40학점"],            # 다전공 자격/학점
    "Q15": ["조기졸업", "4.0이상"],                    # 조기졸업 요건
    "Q16": ["학점초과신청", "3.7이상"],                 # 학점초과 신청
    "Q17": ["군입대", "100%"],                         # 군입대 성적인정
    "Q18": ["미졸업자", "1/6"],                        # 미졸업자 차등등록금
    "Q19": ["공인결석", "결혼일포함7일"],               # 공인결석 인정기간
    "Q20": ["수강신청", "wsugang"],                    # 수강신청 방법
}


def squash(text: str) -> str:
    return re.sub(r"\s+", "", text)


def is_answer(text: str, keywords: list[str]) -> bool:
    body = squash(text)
    return all(squash(k) in body for k in keywords)


# 답이 두 섹션에 나뉘어 있어 한 청크로는 완결되지 않는 질문:
# 키워드 묶음마다 그 묶음을 모두 가진 청크가 있어야 하고, 정답 순위는 가장 늦게 나온 묶음의 순위
MULTI_PART_KEYWORDS: dict[str, list[list[str]]] = {
    # 다전공 > (2) 신청자격(3~8학기) + (5) 학점이수(40학점)
    "Q14": [["다전공", "3~8학기"], ["다전공", "40학점"]],
}

RESULT_PATH = BACKEND_DIR / "evaluation" / "auto_checklist_result.csv"
REVIEW_PATH = BACKEND_DIR / "evaluation" / "auto_checklist_review.csv"
LOG_PATH = BACKEND_DIR / "evaluation" / "auto_checklist_console.txt"


@dataclass
class Hit:
    rank: int
    page: str
    score: str
    article: str
    text: str          # 청크 전문
    is_answer: bool


@dataclass
class AutoResult:
    row: ChecklistRow
    keywords: list[str]
    verdict: str
    rank_of_answer: str
    hits: list[Hit] = field(default_factory=list)

    @property
    def top1(self) -> Hit | None:
        return self.hits[0] if self.hits else None


def evaluate_row(row: ChecklistRow, *, school_id: str) -> AutoResult:
    parts = MULTI_PART_KEYWORDS.get(row.id) or [ANSWER_KEYWORDS.get(row.id, [])]
    keywords = [" / ".join(" + ".join(part) for part in parts)] if len(parts) > 1 else parts[0]
    if not parts[0]:
        raise ValueError(f"{row.id}: 정답 키워드가 정의되지 않았습니다 (ANSWER_KEYWORDS).")

    # Top-3 / Top-10 판정을 같은 순위표에서 하도록 n_results=10으로 한 번 검색 (9/7 실험과 동일)
    top10 = search(row.question, n_results=TOP_K_PARTIAL, school_id=school_id)

    hits = [
        Hit(
            rank=rank,
            page=str(result.get("page") or ""),
            score=f"{float(result.get('score') or 0.0):.4f}",
            article=str(result.get("article_title") or result.get("article") or ""),
            text=str(result.get("text") or ""),
            is_answer=any(is_answer(str(result.get("text") or ""), part) for part in parts),
        )
        for rank, result in enumerate(top10, start=1)
    ]

    if not hits:
        return AutoResult(row, keywords, "EMPTY", "", hits)

    # 묶음마다 처음 나온 순위 → 모든 묶음이 나와야 완결, 순위는 그중 가장 늦은 것
    part_ranks = [
        next((hit.rank for hit in hits if is_answer(hit.text, part)), None)
        for part in parts
    ]
    rank = None if None in part_ranks else max(part_ranks)
    if rank is None:
        verdict = "FAIL"
    elif rank <= TOP_K_PASS:
        verdict = "PASS"
    else:
        verdict = "PARTIAL"
    return AutoResult(row, keywords, verdict, str(rank or ""), hits)


def save_results(path: Path, results: list[AutoResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "id", "variant", "question", "verdict", "rank_of_answer",
        "answer_keywords", "expected_page", "top1_page", "top1_score", "top1_article",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            top1 = result.top1
            writer.writerow({
                "id": result.row.id,
                "variant": result.row.variant,
                "question": result.row.question,
                "verdict": result.verdict,
                "rank_of_answer": result.rank_of_answer,
                "answer_keywords": " + ".join(result.keywords),
                "expected_page": result.row.expected_page,
                "top1_page": top1.page if top1 else "",
                "top1_score": top1.score if top1 else "",
                "top1_article": top1.article if top1 else "",
            })


def save_review_csv(path: Path, results: list[AutoResult]) -> None:
    """Top-10 검수용 CSV. 정답 키워드를 모두 가진 청크는 본문 앞에 [정답] 표시."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["id", "variant", "question", "verdict", "rank_of_answer", "answer_keywords", "expected_page"]
    for rank in range(1, TOP_K_PARTIAL + 1):
        fieldnames += [f"top{rank}_page", f"top{rank}_score", f"top{rank}_text"]

    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            row = {
                "id": result.row.id,
                "variant": result.row.variant,
                "question": result.row.question,
                "verdict": result.verdict,
                "rank_of_answer": result.rank_of_answer,
                "answer_keywords": " + ".join(result.keywords),
                "expected_page": result.row.expected_page,
            }
            for hit in result.hits:
                mark = "[정답] " if hit.is_answer else ""
                row[f"top{hit.rank}_page"] = hit.page
                row[f"top{hit.rank}_score"] = hit.score
                row[f"top{hit.rank}_text"] = mark + clean_preview_text(hit.text)
            writer.writerow(row)


def print_review_block(result: AutoResult, index: int, total: int) -> None:
    row = result.row
    label = VARIANT_LABELS.get(row.variant, row.variant)
    print()
    print("=" * 72)
    print(f"[{index}/{total}] {row.id} / {row.variant} ({label}) → {result.verdict}")
    print(f"질문: {row.question}")
    print(
        f"정답 키워드: {' + '.join(result.keywords)} "
        f"| 기대 page={row.expected_page or '-'} | rank={result.rank_of_answer or '-'}"
    )
    print("-" * 72)
    if not result.hits:
        print("  (검색 결과 없음 → EMPTY)")
        return
    for hit in result.hits:
        marker = " [Top-3]" if hit.rank <= TOP_K_PASS else ""
        answer = " ← 정답" if hit.is_answer else ""
        print(f"  #{hit.rank:<2}{marker}  page={hit.page or '-'}  score={hit.score}  article={hit.article or '-'}{answer}")
        print(f"       {clean_preview_text(hit.text) or '(본문 없음)'}")


def print_summary(results: list[AutoResult]) -> None:
    total = len(results)
    counts = {v: sum(1 for r in results if r.verdict == v) for v in ("PASS", "PARTIAL", "FAIL", "EMPTY")}

    print()
    print("| 판정 | 건수 | 비율 |")
    print("| --- | --- | --- |")
    for verdict, count in counts.items():
        print(f"| {verdict} | {count} | {count / total * 100:.1f}% |")

    print()
    print("변형별 PASS:")
    for variant in ("A", "B", "C"):
        subset = [r for r in results if r.row.variant == variant]
        if subset:
            passed = sum(1 for r in subset if r.verdict == "PASS")
            print(f"  {variant} ({VARIANT_LABELS[variant]}): {passed}/{len(subset)} ({passed / len(subset) * 100:.1f}%)")

    print()
    print("질문별 판정 (A / B / C):")
    by_id: dict[str, dict[str, str]] = {}
    for r in results:
        by_id.setdefault(r.row.id, {})[r.row.variant] = r.verdict
    for qid, verdicts in by_id.items():
        print(f"  {qid}: {' / '.join(verdicts.get(v, '-') for v in ('A', 'B', 'C'))}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="9/7 Top-3 검색 정확도 실험 재현 (정답 키워드 자동 판정)")
    parser.add_argument("--checklist", type=Path, default=CHECKLIST_PATH, help=f"질의 CSV (기본: {CHECKLIST_PATH})")
    parser.add_argument("--output", type=Path, default=RESULT_PATH, help=f"판정 결과 CSV (기본: {RESULT_PATH})")
    parser.add_argument("--review-output", type=Path, default=REVIEW_PATH, help=f"Top-10 검수용 CSV (기본: {REVIEW_PATH})")
    parser.add_argument("--log-output", type=Path, default=LOG_PATH, help=f"터미널 출력 txt (기본: {LOG_PATH})")
    parser.add_argument("--no-log", action="store_true", help="터미널 출력 txt 저장 안 함")
    parser.add_argument("--school-id", default=DEFAULT_SCHOOL_ID, help=f"검색 school_id 필터 (기본: {DEFAULT_SCHOOL_ID})")
    parser.add_argument("--quiet", action="store_true", help="Top-10 상세 블록 생략")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    checklist_path = resolve_path(args.checklist)
    output_path = resolve_path(args.output)
    review_path = resolve_path(args.review_output)
    log_path = resolve_path(args.log_output)

    checklist = load_checklist(checklist_path)

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
        print(f"판정: 정답 키워드를 모두 가진 청크가 Top-{TOP_K_PASS}=PASS / Top-{TOP_K_PARTIAL}=PARTIAL / 밖=FAIL / 0건=EMPTY")

        results: list[AutoResult] = []
        for index, row in enumerate(checklist, start=1):
            result = evaluate_row(row, school_id=args.school_id)
            results.append(result)
            if args.quiet:
                print(f"[{index}/{len(checklist)}] {row.id}/{row.variant} → {result.verdict} (rank={result.rank_of_answer or '-'})")
            else:
                print_review_block(result, index, len(checklist))

        save_results(output_path, results)
        save_review_csv(review_path, results)
        print_summary(results)
        print(f"\n판정 결과: {output_path}")
        print(f"Top-10 검수용: {review_path}")
        if log_file is not None:
            print(f"터미널 출력: {log_path}")
        return 0
    finally:
        sys.stdout = original_stdout
        if log_file is not None:
            log_file.close()


if __name__ == "__main__":
    raise SystemExit(main())
