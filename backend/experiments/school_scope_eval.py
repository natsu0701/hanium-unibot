"""
school_id 기반 검색 필터링 동작 확인 스크립트.

사용법 (backend 디렉터리에서):
    python experiments/school_scope_eval.py
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.rag_service import get_collection, search


TEST_QUERY = "휴학 신청 방법"
FILTER_SCHOOL_ID = "konkuk"
COMPARE_SCHOOL_IDS: list[str | None] = ["konkuk", "demo_univ_1", None]


def list_schools() -> list[dict]:
    """
    현재 ChromaDB 컬렉션에서 school_id별 문서(distinct doc_id) 수를 집계합니다.

    doc_id는 PDF 분할 파싱 단위(예: 큰 PDF를 여러 조각으로 나눠 파싱한 경우
    조각마다 별도 doc_id)이므로, 청크(행) 개수가 아니라 doc_id 종류 수를 셉니다.
    """
    collection = get_collection()

    if collection.count() == 0:
        return []

    metadatas = (
        collection.get(include=["metadatas"]).get("metadatas")
        or []
    )

    doc_ids_by_school: dict[str, set[str]] = {}

    for metadata in metadatas:
        school_id = str((metadata or {}).get("school_id") or "")
        doc_id = str((metadata or {}).get("doc_id") or "")

        if not school_id or not doc_id:
            continue

        doc_ids_by_school.setdefault(school_id, set()).add(doc_id)

    return [
        {"id": school_id, "doc_count": len(doc_ids)}
        for school_id, doc_ids in sorted(doc_ids_by_school.items())
    ]


def evaluate() -> None:
    print("=== 학교별 문서 수 (list_schools) ===")
    schools = list_schools()

    if not schools:
        print("저장된 school_id가 없습니다. 더미 데이터 적재 여부를 확인하세요.")
        return

    for school in schools:
        print(f"  {school['id']}: {school['doc_count']}개 문서")

    print(f"\n=== school_id='{FILTER_SCHOOL_ID}' 필터링 검색: '{TEST_QUERY}' ===")
    filtered_results = search(
        TEST_QUERY,
        n_results=5,
        min_score=0.0,
        school_id=FILTER_SCHOOL_ID,
    )

    for result in filtered_results:
        print(
            f"  score={result['score']:.4f} "
            f"school_id={result['school_id']!r} "
            f"article_title={result['article_title']!r}"
        )

    leaked = [
        result
        for result in filtered_results
        if result["school_id"] != FILTER_SCHOOL_ID
    ]
    print(
        f"  -> '{FILTER_SCHOOL_ID}' 이외 school_id 섞임: {len(leaked)}건"
        " (0이어야 정상)"
    )
    assert not leaked, f"필터링 실패: {leaked}"

    print(f"\n=== school_id 필터 없이 검색: '{TEST_QUERY}' ===")
    unfiltered_results = search(
        TEST_QUERY,
        n_results=10,
        min_score=0.0,
    )
    school_ids_seen = sorted(
        {result["school_id"] for result in unfiltered_results}
    )
    print(f"  결과에 섞인 school_id 종류: {school_ids_seen}")
    print(
        "  -> 2개 이상이면 필터 미적용 시 여러 학교가 후보로 등장함을 의미"
        " (필터의 필요성 확인)"
    )


def compare_scopes() -> None:
    scope_labels = [
        scope if scope else "전체(필터 없음)" for scope in COMPARE_SCHOOL_IDS
    ]

    print(
        f"\n=== 동일 질문 스코프별 비교: '{TEST_QUERY}' "
        f"({', '.join(scope_labels)}) ==="
    )

    results_by_label: dict[str, list[dict]] = {}

    for scope, label in zip(COMPARE_SCHOOL_IDS, scope_labels):
        results = search(
            TEST_QUERY,
            n_results=5,
            min_score=0.0,
            school_id=scope,
        )
        results_by_label[label] = results

        top_text = results[0]["text"][:40] if results else None
        print(f"  [{label}] {len(results)}건, top1={top_text!r}")

    signatures = {
        label: tuple(
            (result["doc_id"], result["article"], result["page"])
            for result in results
        )
        for label, results in results_by_label.items()
    }

    scoped_labels = [
        (scope, label)
        for scope, label in zip(COMPARE_SCHOOL_IDS, scope_labels)
        if scope is not None
    ]

    # 서로 다른 school_id로 필터링한 결과는 겹치는 문서 집합이 없으므로
    # 반드시 달라야 합니다 (강한 보장).
    scoped_all_different = True

    for i, (_, label_a) in enumerate(scoped_labels):
        for _, label_b in scoped_labels[i + 1:]:
            if signatures[label_a] == signatures[label_b]:
                scoped_all_different = False
                print(f"  -> 오류: '{label_a}'와 '{label_b}' 결과가 동일합니다.")

    print(f"  -> 학교별 필터링 결과가 서로 다름: {scoped_all_different}")
    assert scoped_all_different, (
        "서로 다른 school_id 필터링 결과가 겹칩니다 (필터링 실패)."
    )

    # 필터 없음(전체) 결과는 상위 점수가 특정 학교로 쏠리면 그 학교의
    # 필터링 결과와 우연히 같을 수 있습니다. 데이터 편중에 따른 정상
    # 현상이므로 경고만 남기고 실패로 취급하지 않습니다.
    unscoped_label = next(
        label
        for scope, label in zip(COMPARE_SCHOOL_IDS, scope_labels)
        if scope is None
    )

    for _, scoped_label in scoped_labels:
        if signatures[unscoped_label] == signatures[scoped_label]:
            print(
                f"  -> 참고: '{unscoped_label}' 결과가 '{scoped_label}'와"
                " 동일합니다 (해당 학교 데이터가 상위 점수를 독점 — 정상일 수 있음)."
            )


if __name__ == "__main__":
    evaluate()
    compare_scopes()