"""
표 파싱 개선 후 검색 정확도 측정 스크립트.

사용법 (backend 디렉터리에서):
    python experiments/table_search_eval.py
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.rag_service import search


# (질문, 표 청크가 Top 결과에 포함되어야 하는지)
TEST_QUERIES: list[tuple[str, bool]] = [
    ("전공기초 학점은?", True),
    ("학사경고 평점 기준", True),
    ("공인결석 인정기간은?", True),
    ("성적 등급별 평점은?", True),
    ("상대평가 A등급 비율은?", True),
    ("휴학은 최대 몇 학기?", False),
    ("수강신청이란 무엇인가?", False),
    ("초과이수 가능한 평점 기준은?", False),
]

TOP_N = 3
# Top-N 밖으로 밀린 표 청크의 실제 순위를 확인하기 위한 후보 풀 크기.
# min_score=0.0으로 조회해 점수 임계값 때문에 잘리는 경우를 배제한다.
CANDIDATE_POOL_SIZE = 15


def find_table_rank(candidates: list[dict]) -> int | None:
    """
    후보 목록에서 처음 등장하는 표 청크의 1-based 순위를 반환합니다.
    표 청크가 없으면 None을 반환합니다.
    """
    for rank, item in enumerate(candidates, start=1):
        if item.get("is_table"):
            return rank

    return None


def evaluate() -> None:
    rows: list[tuple[str, bool, int, float | None, bool, bool, int | None]] = []

    for query, expects_table in TEST_QUERIES:
        candidates = search(
            query,
            n_results=CANDIDATE_POOL_SIZE,
            min_score=0.0,
        )
        top_n = candidates[:TOP_N]

        table_count = sum(
            1 for item in top_n if item.get("is_table")
        )
        top1_score = (
            float(top_n[0]["score"]) if top_n else None
        )
        top1_is_table = bool(
            top_n and top_n[0].get("is_table")
        )
        # Top-N 안에 표 청크가 하나라도 있는지
        # (1등이 아니어도 "밀리지 않고 후보에는 들었는지" 확인용)
        top3_has_table = table_count > 0
        # 후보 풀(CANDIDATE_POOL_SIZE) 전체에서 표 청크의 실제 순위.
        # Top-N 안에 없더라도 몇 등까지 밀렸는지 직접 확인한다.
        table_rank = find_table_rank(candidates)

        rows.append(
            (
                query,
                expects_table,
                table_count,
                top1_score,
                top1_is_table,
                top3_has_table,
                table_rank,
            )
        )

    print(
        f"| 질문 | 표 기대 여부 | Top-{TOP_N} 중 표 개수 "
        f"| Top-1 점수 | Top-1이 표 | Top-{TOP_N}에 표 포함 | 표 청크 실제 순위 |"
    )
    print("|---|---|---:|---:|---|---|---:|")

    for query, expects_table, table_count, top1_score, top1_is_table, top3_has_table, table_rank in rows:
        expects_label = "Yes" if expects_table else "No"
        score_label = (
            f"{top1_score:.4f}" if top1_score is not None else "-"
        )
        top1_label = "O" if top1_is_table else "X"
        top3_label = "O" if top3_has_table else "X"
        rank_label = (
            str(table_rank)
            if table_rank is not None
            else f"없음(Top-{CANDIDATE_POOL_SIZE} 밖)"
        )
        print(
            f"| {query} | {expects_label} | {table_count} "
            f"| {score_label} | {top1_label} | {top3_label} | {rank_label} |"
        )

    # 표를 기대한 질문들만 추려서 성공률 계산
    expected_rows = [row for row in rows if row[1]]  # expects_table=True
    total = len(expected_rows)

    top1_hit_count = sum(1 for row in expected_rows if row[4])  # top1_is_table
    top3_hit_count = sum(1 for row in expected_rows if row[5])  # top3_has_table

    top1_rate = (top1_hit_count / total * 100.0) if total else 0.0
    top3_rate = (top3_hit_count / total * 100.0) if total else 0.0

    # Top-N 밖으로 밀린 질문들의 실제 순위 분포
    # (근소하게 밀린 건지, 완전히 밀린 건지 구분)
    pushed_down_rows = [
        row for row in expected_rows if row[6] is not None and row[6] > TOP_N
    ]
    not_found_rows = [row for row in expected_rows if row[6] is None]

    # 표를 기대하지 않은 질문인데 표가 Top-1로 잘못 나온 경우
    # (표 파싱 개선이 조문 검색을 오히려 망가뜨렸는지 확인)
    non_table_rows = [row for row in rows if not row[1]]  # expects_table=False
    false_positive_count = sum(1 for row in non_table_rows if row[4])  # top1_is_table

    print()
    print(
        f"Top-1 적중률 (표가 1등으로 나옴): "
        f"{top1_hit_count}/{total}개 ({top1_rate:.1f}%)"
    )
    print(
        f"Top-{TOP_N} 포함률 (표가 {TOP_N}등 안에라도 있음): "
        f"{top3_hit_count}/{total}개 ({top3_rate:.1f}%)"
    )

    if pushed_down_rows:
        print(f"Top-{TOP_N} 밖으로 밀린 질문의 실제 순위:")
        for query, *_rest, table_rank in pushed_down_rows:
            print(f"  - {query}: {table_rank}위")

    if not_found_rows:
        print(
            f"Top-{CANDIDATE_POOL_SIZE} 안에서도 표 청크를 찾지 못한 질문: "
            f"{len(not_found_rows)}개"
        )
        for query, *_rest in not_found_rows:
            print(f"  - {query}")

    print(
        f"오탐 (표를 기대 안 한 질문인데 표가 Top-1로 나옴): "
        f"{false_positive_count}/{len(non_table_rows)}개"
        " (0이어야 정상 — 조문 검색이 표에 밀리지 않았는지 확인)"
    )


if __name__ == "__main__":
    evaluate()