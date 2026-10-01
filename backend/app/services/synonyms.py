from __future__ import annotations


SYNONYM_MAP: dict[str, list[str]] = {
    "최대 학점": [
        "한도학점",
        "신청학점 한도",
        "수강신청 한도",
    ],
    "성적 정정": [
        "성적 이의신청",
        "성적 이의",
    ],
    "다전공": [
        "복수전공",
        "부전공",
        "연계전공",
    ],
    "휴학 종류": [
        "일반휴학",
        "군휴학",
        "질병휴학",
    ],
    "수강신청": [
        "수강 신청",
        "수강등록",
    ],
    "졸업 학점": [
        "졸업이수학점",
        "졸업 이수 학점",
        "졸업요건 학점",
    ],
    "장학금": [
        "장학",
        "장학생",
    ],
    "복학": [
        "복학신청",
        "복학 신청",
    ],
    "휴학": [
        "휴학신청",
        "휴학 신청",
    ],
    "전과": [
        "전공변경",
        "학과변경",
    ],
    "재수강": [
        "재이수",
        "재수강 신청",
    ],
    "학점 포기": [
        "학점삭제",
        "성적포기",
    ],
    "수료": [
        "수료요건",
        "수료 기준",
    ],
    "졸업": [
        "졸업요건",
        "졸업 기준",
    ],
    "학사경고": [
        "성적경고",
        "학업경고",
    ],
}


def expand_query(query: str) -> str:
    """
    사용자 질문에 동의어를 추가해 검색 질의를 확장합니다.

    예:
    "수강신청 최대 학점 알려줘"
    ->
    "수강신청 최대 학점 알려줘 한도학점 신청학점 한도 ..."
    """

    query = query.strip()

    if not query:
        return query

    expanded_terms: list[str] = []

    for key, synonyms in SYNONYM_MAP.items():
        if key in query:
            for synonym in synonyms:
                if synonym not in expanded_terms:
                    expanded_terms.append(synonym)

    if not expanded_terms:
        return query

    return " ".join(
        [query] + expanded_terms
    )