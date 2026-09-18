from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


# =========================================================
# 환경변수
# =========================================================

BACKEND_DIR = Path(__file__).resolve().parents[2]

load_dotenv(
    BACKEND_DIR / ".env"
)


DEFAULT_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-4o-mini",
)

VERIFICATION_MODEL = os.getenv(
    "OPENAI_VERIFICATION_MODEL",
    "gpt-4o-mini",
)


def get_float_env(
    name: str,
    default: float,
) -> float:
    """
    환경변수를 float으로 읽습니다.

    잘못된 값이 입력되면 default를 반환합니다.
    """
    try:
        return float(
            os.getenv(
                name,
                str(default),
            )
        )

    except (TypeError, ValueError):
        return default


SELF_RAG_THRESHOLD = get_float_env(
    "SELF_RAG_THRESHOLD",
    0.7,
)


# =========================================================
# 답변 생성 시스템 프롬프트
# =========================================================

SYSTEM_PROMPT = """
당신은 대학 학사 규정을 학생에게 쉽게 설명하는 Uni-Bot입니다.

반드시 다음 규칙을 지키세요.

1. 검색된 문서 내용을 그대로 길게 복사하지 마세요.
2. 사용자의 질문에 직접 필요한 내용만 추려서 답하세요.
3. 답변은 기본적으로 2~4문장으로 작성하세요.
4. 결론을 첫 문장에 먼저 말하세요.
5. 조건, 기간, 예외가 있으면 짧게 덧붙이세요.
6. 원문 조항 전체를 나열하거나 붙여넣지 마세요.
7. 문서에서 확인되지 않은 내용은 추측하지 마세요.
8. 사용한 근거 번호만 used_source_indexes에 넣으세요.
9. 근거 번호는 0부터 시작합니다.
10. confidence는 0.0부터 1.0 사이 숫자입니다.

학교 관련 규칙:
11. 현재 답변 대상 학교가 지정되어 있다면
    반드시 해당 학교의 검색 근거만 사용하세요.
12. 검색된 근거의 학교와 다른 학교의 규정을
    임의로 언급하거나 섞지 마세요.
13. 다른 학교의 일반적인 규정을 추측해서
    보완하지 마세요.

표 자료 관련 규칙:
14. 표 자료를 사용할 때는 반드시
    헤더와 값의 관계를 정확하게 해석하세요.
15. 숫자, 등급, 학점, 기간, 비율 등의 값은
    표에 실제로 기재된 값을 그대로 사용하세요.
16. 표에서 어떤 값이 어떤 헤더에 해당하는지
    불명확한 경우 추측하지 마세요.
17. 예를 들어
    "전공기초 / 학점 3 / 이수구분 필수"
    라는 표 근거가 있다면
    "전공기초는 3학점이며 필수입니다."
    처럼 헤더와 값의 관계를 유지해서 답하세요.

반드시 아래 JSON 객체만 반환하세요.

{
  "answer": "학생에게 보여줄 간결한 최종 답변",
  "used_source_indexes": [0],
  "confidence": 0.9
}
""".strip()


# =========================================================
# Self-RAG 검증 시스템 프롬프트
# =========================================================

VERIFICATION_SYSTEM_PROMPT = """
당신은 대학 학사규정 RAG 답변 검증기입니다.

사용자 질문, 검색 근거, 생성 답변을 검토하고
답변이 근거로 직접 뒷받침되는지 판단하세요.

판정 규칙:

1. 검색 근거에 없는 구체적 사실, 금액, 일정,
   숫자, 기준 또는 개인 결과를 답변하면
   supported=false입니다.

2. "다음 학기 등록금이 얼마인가요?"처럼
   근거에 정확한 금액이 없으면
   supported=false입니다.

3. "내 성적으로 장학금을 받을 수 있나요?"처럼
   개인 성적 또는 개인 조건이 필요한 질문은
   supported=false입니다.

4. "교수님이 승인해 주실까요?"처럼
   미래의 개인 판단을 예측하면
   supported=false입니다.

5. 질문은 성적 정정인데 근거가 수강신청 정정에
   관한 내용이라면 supported=false입니다.

6. 답변 전체의 핵심 내용이 검색 근거에
   직접 포함되거나 명확히 뒷받침될 때만
   supported=true입니다.

학교 관련 검증 규칙:

7. 대상 학교가 명시되어 있다면
   답변이 해당 학교 근거만 사용했는지 확인하세요.

8. 답변이 대상 학교가 아닌 다른 학교의 규정을
   언급하거나 섞었다면 supported=false입니다.

표 자료 관련 검증 규칙:

9. 표를 근거로 한 답변이라면
   헤더와 값의 매핑이 정확한지 확인하세요.

10. 표의 숫자, 학점, 등급, 기간, 비율 등을
    잘못 연결했거나 표에 없는 숫자를 생성했다면
    supported=false입니다.

11. 표에 값은 있으나 어떤 헤더에 속하는지
    명확하지 않은데 답변이 이를 단정했다면
    supported=false입니다.

12. verification_score는
    0.0~1.0 사이 숫자입니다.

반드시 아래 JSON 객체만 반환하세요.

{
  "supported": true,
  "score": 0.85,
  "reason": "검색 근거가 답변을 직접 뒷받침함"
}
""".strip()


# =========================================================
# OpenAI Client
# =========================================================

def get_openai_client() -> OpenAI:
    """
    환경변수에서 OpenAI API Key를 읽어
    클라이언트를 생성합니다.
    """
    api_key = os.getenv(
        "OPENAI_API_KEY",
        "",
    ).strip()

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY가 설정되지 않았습니다. "
            "backend/.env 파일을 확인해주세요."
        )

    return OpenAI(
        api_key=api_key
    )


# =========================================================
# 공통 유틸
# =========================================================

def clean_text(
    text: str,
    max_length: int = 6000,
) -> str:
    """
    일반 문서 본문의 과도한 공백을 정리합니다.
    """
    cleaned = re.sub(
        r"\s+",
        " ",
        str(text or ""),
    ).strip()

    return cleaned[:max_length]


def clean_table_text(
    text: str,
    max_length: int = 6000,
) -> str:
    """
    표 청크는 행 단위 줄바꿈이 중요하므로
    줄바꿈을 최대한 보존합니다.
    """
    raw = str(
        text or ""
    ).strip()

    if not raw:
        return ""

    lines: list[str] = []

    for line in raw.splitlines():
        cleaned_line = re.sub(
            r"[ \t]+",
            " ",
            line,
        ).strip()

        if cleaned_line:
            lines.append(
                cleaned_line
            )

    return "\n".join(
        lines
    )[:max_length]


def normalize_table_headers(
    value: Any,
) -> list[str]:
    """
    table_headers를 안전한 문자열 목록으로 변환합니다.
    """
    if not isinstance(
        value,
        list,
    ):
        return []

    headers: list[str] = []

    for item in value:
        text = str(
            item or ""
        ).strip()

        if (
            text
            and text not in headers
        ):
            headers.append(
                text
            )

    return headers


# =========================================================
# RAG Context 생성
# =========================================================

def build_context(
    search_results: list[dict[str, Any]],
) -> str:
    """
    검색 결과를 OpenAI가 이해하기 좋은
    근거 문자열로 변환합니다.

    일반 조문과 표 자료를 서로 다른 포맷으로 처리합니다.
    """
    if not search_results:
        return (
            "검색된 문서 근거가 없습니다."
        )

    context_parts: list[str] = []

    for index, result in enumerate(
        search_results
    ):
        doc_name = str(
            result.get(
                "doc_name"
            )
            or "문서명 없음"
        ).strip()

        try:
            page = int(
                result.get(
                    "page"
                )
                or 0
            )

        except (
            TypeError,
            ValueError,
        ):
            page = 0

        school_id = str(
            result.get(
                "school_id"
            )
            or ""
        ).strip()

        chapter_title = str(
            result.get(
                "chapter_title"
            )
            or ""
        ).strip()

        article = str(
            result.get(
                "article"
            )
            or ""
        ).strip()

        article_title = str(
            result.get(
                "article_title"
            )
            or ""
        ).strip()

        is_table = (
            result.get(
                "is_table"
            )
            is True
        )

        table_headers = (
            normalize_table_headers(
                result.get(
                    "table_headers"
                )
            )
        )

        table_summary = str(
            result.get(
                "table_summary"
            )
            or ""
        ).strip()

        # =============================================
        # 표 청크
        # =============================================

        if is_table:
            table_text = clean_table_text(
                str(
                    result.get(
                        "text"
                    )
                    or ""
                ),
                max_length=5000,
            )

            source_lines = [
                f"[근거 {index}] (표 자료)",
                f"문서명: {doc_name}",
                f"페이지: {page}",
            ]

            if school_id:
                source_lines.append(
                    f"학교 ID: {school_id}"
                )

            if chapter_title:
                source_lines.append(
                    f"장 제목: {chapter_title}"
                )

            if article:
                normalized_article = article

                if not (
                    normalized_article
                    .startswith("제")
                ):
                    normalized_article = (
                        f"제{normalized_article}"
                    )

                if not (
                    normalized_article
                    .endswith("조")
                ):
                    normalized_article = (
                        f"{normalized_article}조"
                    )

                source_lines.append(
                    f"조항: {normalized_article}"
                )

            if article_title:
                source_lines.append(
                    f"조 제목: {article_title}"
                )

            if table_headers:
                source_lines.append(
                    "표 헤더: "
                    + ", ".join(
                        table_headers
                    )
                )

            if table_summary:
                source_lines.append(
                    f"표 요약: {table_summary}"
                )

            source_lines.extend(
                [
                    "표 내용:",
                    table_text,
                ]
            )

            context_parts.append(
                "\n".join(
                    source_lines
                )
            )

            continue

        # =============================================
        # 일반 조문 청크
        # =============================================

        text = clean_text(
            str(
                result.get(
                    "text"
                )
                or ""
            ),
            max_length=4000,
        )

        source_lines = [
            f"[근거 {index}]",
            f"문서명: {doc_name}",
            f"페이지: {page}",
        ]

        if school_id:
            source_lines.append(
                f"학교 ID: {school_id}"
            )

        if chapter_title:
            source_lines.append(
                f"장 제목: {chapter_title}"
            )

        if article:
            normalized_article = article

            if not (
                normalized_article
                .startswith("제")
            ):
                normalized_article = (
                    f"제{normalized_article}"
                )

            if not (
                normalized_article
                .endswith("조")
            ):
                normalized_article = (
                    f"{normalized_article}조"
                )

            source_lines.append(
                f"조항: {normalized_article}"
            )

        if article_title:
            source_lines.append(
                f"조 제목: {article_title}"
            )

        source_lines.append(
            f"내용: {text}"
        )

        context_parts.append(
            "\n".join(
                source_lines
            )
        )

    return "\n\n".join(
        context_parts
    )


# =========================================================
# JSON 응답 처리
# =========================================================

def extract_json_object(
    raw_text: str,
) -> dict[str, Any]:
    """
    모델 응답에서 JSON 객체를 추출합니다.
    """
    text = str(
        raw_text or ""
    ).strip()

    if text.startswith(
        "```"
    ):
        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"\s*```$",
            "",
            text,
        )

    try:
        parsed = json.loads(
            text
        )

        if isinstance(
            parsed,
            dict,
        ):
            return parsed

    except json.JSONDecodeError:
        pass

    start_index = text.find(
        "{"
    )

    end_index = text.rfind(
        "}"
    )

    if (
        start_index != -1
        and end_index != -1
        and start_index
        < end_index
    ):
        json_text = text[
            start_index:
            end_index + 1
        ]

        try:
            parsed = json.loads(
                json_text
            )

            if isinstance(
                parsed,
                dict,
            ):
                return parsed

        except json.JSONDecodeError:
            pass

    raise RuntimeError(
        "OpenAI 응답을 JSON으로 해석하지 못했습니다."
    )


def normalize_used_indexes(
    value: Any,
    result_count: int,
) -> list[int]:
    """
    모델이 반환한 근거 번호를 검증합니다.
    """
    if not isinstance(
        value,
        list,
    ):
        return []

    normalized: list[int] = []

    for item in value:
        try:
            index = int(
                item
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

        if (
            0 <= index < result_count
            and index
            not in normalized
        ):
            normalized.append(
                index
            )

    return normalized


def normalize_confidence(
    value: Any,
) -> float:
    """
    confidence 값을 0.0~1.0 범위로 정리합니다.
    """
    try:
        confidence = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        return 0.0

    return max(
        0.0,
        min(
            confidence,
            1.0,
        ),
    )


def normalize_supported(
    value: Any,
) -> bool:
    """
    supported 값을 bool로 정리합니다.
    """
    if isinstance(
        value,
        bool,
    ):
        return value

    if isinstance(
        value,
        str,
    ):
        normalized = (
            value
            .strip()
            .lower()
        )

        if normalized in {
            "true",
            "1",
            "yes",
            "y",
        }:
            return True

        if normalized in {
            "false",
            "0",
            "no",
            "n",
        }:
            return False

    return False


# =========================================================
# Self-RAG 검증
# =========================================================

def verify_answer(
    question: str,
    search_results: list[dict[str, Any]],
    answer: str,
    school_name: str | None = None,
) -> dict[str, Any]:
    """
    질문, 검색 근거, 생성 답변이
    실제로 일치하는지 검증합니다.
    """
    client = get_openai_client()

    school_scope = ""

    if (
        school_name
        and school_name.strip()
    ):
        school_scope = f"""
[현재 답변 대상 학교]
{school_name.strip()}

위 학교의 규정만 답변 근거로 인정하세요.
다른 학교 규정이 답변에 섞이면
supported=false로 판정하세요.
""".strip()

    verification_prompt = f"""
{school_scope}

[사용자 질문]
{question}

[생성 답변]
{answer}

[검색된 문서 근거]
{build_context(search_results)}

위 답변이 검색된 문서 근거로
직접 뒷받침되는지 엄격하게 검증하세요.

특히 다음을 확인하세요.

- 근거에 없는 숫자나 조건을 추가하지 않았는가
- 질문과 실제 근거가 동일한 주제인가
- 표 자료를 사용했다면 헤더와 값의 매핑이 정확한가
- 대상 학교가 지정된 경우 다른 학교 규정을 섞지 않았는가

반드시 아래 JSON 객체만 반환하세요.

{{
  "supported": true,
  "score": 0.82,
  "reason": "근거가 답변을 직접 뒷받침함"
}}
""".strip()

    try:
        response = (
            client
            .chat
            .completions
            .create(
                model=VERIFICATION_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": VERIFICATION_SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": verification_prompt,
                    },
                ],
                response_format={
                    "type": "json_object",
                },
                temperature=0,
            )
        )

        raw_text = str(
            response
            .choices[0]
            .message
            .content
            or ""
        ).strip()

        if not raw_text:
            raise RuntimeError(
                "검증 모델이 빈 응답을 반환했습니다."
            )

        parsed = extract_json_object(
            raw_text
        )

    except Exception as exc:
        print(
            "[WARN] Self-RAG 답변 검증 실패 "
            f"(검증을 통과한 것으로 처리): {exc}"
        )

        # 검증 API 자체 장애가
        # 정상 답변을 막지 않도록 통과 처리
        return {
            "supported": True,
            "score": 1.0,
            "reason": (
                "검증 과정에서 오류가 발생해 "
                "사용자 경험을 위해 통과 처리했습니다."
            ),
        }

    supported = normalize_supported(
        parsed.get(
            "supported"
        )
    )

    score = normalize_confidence(
        parsed.get(
            "score",
            parsed.get(
                "verification_score",
                0.0,
            ),
        )
    )

    reason = str(
        parsed.get(
            "reason"
        )
        or ""
    ).strip()

    return {
        "supported": supported,
        "score": score,
        "reason": reason,
    }


# =========================================================
# 최종 답변 생성
# =========================================================

def generate_answer(
    question: str,
    search_results: list[dict[str, Any]],
    school_name: str | None = None,
) -> dict[str, Any]:
    """
    검색된 청크를 기반으로
    OpenAI 최종 답변을 생성합니다.

    school_name이 전달되면
    해당 학교 규정으로 답변 범위를 제한합니다.
    """
    question = str(
        question or ""
    ).strip()

    if not question:
        raise ValueError(
            "질문이 비어 있습니다."
        )

    if not search_results:
        return {
            "answer": (
                "제공된 학사규정에서 해당 질문을 "
                "뒷받침할 근거를 찾기 어렵습니다."
            ),
            "used_source_indexes": [],
            "confidence": 0.0,
            "verification_score": 0.0,
            "rejection_reason": "unsupported",
        }

    client = get_openai_client()

    context = build_context(
        search_results
    )

    school_scope = ""

    if (
        school_name
        and school_name.strip()
    ):
        school_scope = f"""
현재 답변 대상:
{school_name.strip()} 학생

다른 학교의 규정은 절대 참고하거나
추측하지 말고,
아래 검색된 근거만으로 답변하세요.
""".strip()

    user_prompt = f"""
{school_scope}

사용자 질문:
{question}

검색된 문서 근거:
{context}

위 근거를 검토하여
사용자의 질문에 답변하세요.

답변 작성 기준:

- 검색된 근거에 나온 내용만 사용하세요.
- 중요한 조건이나 예외가 있으면 함께 설명하세요.
- 불필요하게 길게 작성하지 마세요.
- 실제로 답변에 사용한 근거 번호만 선택하세요.
- 표 자료가 있다면 헤더와 값의 관계를 정확히 유지하세요.
- 표의 숫자, 학점, 등급, 기간, 비율은 근거의 값을 정확히 옮기세요.
- 대상 학교가 명시된 경우 다른 학교 규정은 절대 언급하지 마세요.
- 반드시 JSON 객체만 반환하세요.
""".strip()

    try:
        response = (
            client
            .responses
            .create(
                model=DEFAULT_MODEL,
                instructions=SYSTEM_PROMPT,
                input=user_prompt,
                store=False,
            )
        )

    except Exception as exc:
        raise RuntimeError(
            "OpenAI 답변 생성에 실패했습니다: "
            f"{exc}"
        ) from exc

    raw_text = str(
        response.output_text
        or ""
    ).strip()

    if not raw_text:
        raise RuntimeError(
            "OpenAI에서 빈 응답을 반환했습니다."
        )

    parsed = extract_json_object(
        raw_text
    )

    answer = str(
        parsed.get(
            "answer"
        )
        or ""
    ).strip()

    if not answer:
        raise RuntimeError(
            "OpenAI 응답에 answer 값이 없습니다."
        )

    used_source_indexes = (
        normalize_used_indexes(
            parsed.get(
                "used_source_indexes"
            ),
            len(
                search_results
            ),
        )
    )

    answer_confidence = (
        normalize_confidence(
            parsed.get(
                "confidence"
            )
        )
    )

    # 실제 사용했다고 선택한 근거만
    # 검증 모델에 전달
    used_chunks = [
        search_results[index]
        for index in used_source_indexes
    ]

    # 모델이 근거 번호를 하나도 선택하지 않았다면
    # 검색 결과 전체를 검증에 사용
    verification_chunks = (
        used_chunks
        if used_chunks
        else search_results
    )

    verification_result = (
        verify_answer(
            question=question,
            search_results=verification_chunks,
            answer=answer,
            school_name=school_name,
        )
    )

    supported = normalize_supported(
        verification_result.get(
            "supported"
        )
    )

    verification_score = (
        normalize_confidence(
            verification_result.get(
                "score"
            )
        )
    )

    print(
        "[INFO] Self-RAG 검증 결과: "
        f"supported={supported}, "
        f"score={verification_score:.3f}, "
        f"reason={verification_result.get('reason', '')}"
    )

    if (
        not supported
        or verification_score
        < SELF_RAG_THRESHOLD
    ):
        rejection_reason = (
            "unsupported"
            if not supported
            else "low_score"
        )

        return {
            "answer": (
                "검색된 문서에서 답변을 뒷받침할 "
                "충분한 근거를 찾지 못했습니다."
            ),
            "used_source_indexes": [],
            "confidence": verification_score,
            "verification_score": verification_score,
            "rejection_reason": rejection_reason,
        }

    final_confidence = (
        answer_confidence
        + verification_score
    ) / 2

    final_confidence = round(
        final_confidence,
        3,
    )

    return {
        "answer": answer,
        "used_source_indexes": used_source_indexes,
        "confidence": final_confidence,
        "verification_score": verification_score,
        "rejection_reason": None,
    }