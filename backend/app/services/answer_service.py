from __future__ import annotations

import json
import os
import re
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


DEFAULT_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-4o-mini",
)


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
11. 반드시 아래 JSON 객체만 반환하세요.

{
  "answer": "학생에게 보여줄 간결한 최종 답변",
  "used_source_indexes": [0],
  "confidence": 0.9
}
""".strip()


def get_openai_client() -> OpenAI:
    """
    환경변수에서 API 키를 읽어 OpenAI 클라이언트를 생성합니다.
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


def clean_text(
    text: str,
    max_length: int = 6000,
) -> str:
    """
    문서 본문의 과도한 공백을 정리하고 길이를 제한합니다.
    """
    cleaned = re.sub(
        r"\s+",
        " ",
        str(text or ""),
    ).strip()

    return cleaned[:max_length]


def build_context(
    search_results: list[dict[str, Any]],
) -> str:
    """
    검색 결과를 OpenAI에 전달할 근거 문자열로 변환합니다.
    """
    if not search_results:
        return "검색된 문서 근거가 없습니다."

    context_parts: list[str] = []

    for index, result in enumerate(
        search_results
    ):
        doc_name = str(
            result.get("doc_name") or "문서명 없음"
        )

        page = int(
            result.get("page") or 0
        )

        chapter_title = str(
            result.get("chapter_title") or ""
        ).strip()

        article = str(
            result.get("article") or ""
        ).strip()

        article_title = str(
            result.get("article_title") or ""
        ).strip()

        text = clean_text(
            str(result.get("text") or ""),
            max_length=4000,
        )

        source_lines = [
            f"[근거 {index}]",
            f"문서명: {doc_name}",
            f"페이지: {page}",
        ]

        if chapter_title:
            source_lines.append(
                f"장 제목: {chapter_title}"
            )

        if article:
            source_lines.append(
                f"조항: 제{article}조"
            )

        if article_title:
            source_lines.append(
                f"조 제목: {article_title}"
            )

        source_lines.append(
            f"내용: {text}"
        )

        context_parts.append(
            "\n".join(source_lines)
        )

    return "\n\n".join(context_parts)


def extract_json_object(
    raw_text: str,
) -> dict[str, Any]:
    """
    모델 응답에서 JSON 객체를 추출합니다.
    """
    text = raw_text.strip()

    if text.startswith("```"):
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
        parsed = json.loads(text)

        if isinstance(parsed, dict):
            return parsed

    except json.JSONDecodeError:
        pass

    start_index = text.find("{")
    end_index = text.rfind("}")

    if (
        start_index != -1
        and end_index != -1
        and start_index < end_index
    ):
        json_text = text[
            start_index:end_index + 1
        ]

        try:
            parsed = json.loads(
                json_text
            )

            if isinstance(parsed, dict):
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
    모델이 반환한 출처 번호를 검증합니다.
    """
    if not isinstance(value, list):
        return []

    normalized: list[int] = []

    for item in value:
        try:
            index = int(item)

        except (TypeError, ValueError):
            continue

        if (
            0 <= index < result_count
            and index not in normalized
        ):
            normalized.append(index)

    return normalized


def normalize_confidence(
    value: Any,
) -> float:
    """
    confidence 값을 0.0~1.0 범위로 정리합니다.
    """
    try:
        confidence = float(value)

    except (TypeError, ValueError):
        return 0.0

    return max(
        0.0,
        min(confidence, 1.0),
    )


def generate_answer(
    question: str,
    search_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    검색된 청크를 기반으로 OpenAI 최종 답변을 생성합니다.

    반환값:
    {
        "answer": "...",
        "used_source_indexes": [0, 1],
        "confidence": 0.85
    }
    """
    question = question.strip()

    if not question:
        raise ValueError(
            "질문이 비어 있습니다."
        )

    if not search_results:
        return {
            "answer": (
                "질문과 관련된 학사 규정 근거를 "
                "찾지 못했습니다. 질문을 조금 더 "
                "구체적으로 입력해주세요."
            ),
            "used_source_indexes": [],
            "confidence": 0.0,
        }

    client = get_openai_client()
    context = build_context(
        search_results
    )

    user_prompt = f"""
사용자 질문:
{question}

검색된 문서 근거:
{context}

위 근거를 검토하여 사용자의 질문에 답변하세요.

답변 작성 기준:
- 근거에 나온 내용만 사용하세요.
- 중요한 조건이나 예외가 있으면 함께 설명하세요.
- 불필요하게 길게 작성하지 마세요.
- 실제로 답변에 사용한 근거 번호만 선택하세요.
- 반드시 JSON 객체만 반환하세요.
""".strip()

    try:
        response = client.responses.create(
            model=DEFAULT_MODEL,
            instructions=SYSTEM_PROMPT,
            input=user_prompt,
            store=False,
        )

    except Exception as exc:
        raise RuntimeError(
            f"OpenAI 답변 생성에 실패했습니다: {exc}"
        ) from exc

    raw_text = str(
        response.output_text or ""
    ).strip()

    if not raw_text:
        raise RuntimeError(
            "OpenAI에서 빈 응답을 반환했습니다."
        )

    parsed = extract_json_object(
        raw_text
    )

    answer = str(
        parsed.get("answer") or ""
    ).strip()

    if not answer:
        raise RuntimeError(
            "OpenAI 응답에 answer 값이 없습니다."
        )

    used_source_indexes = normalize_used_indexes(
        parsed.get("used_source_indexes"),
        len(search_results),
    )

    confidence = normalize_confidence(
        parsed.get("confidence")
    )

    return {
        "answer": answer,
        "used_source_indexes": used_source_indexes,
        "confidence": confidence,
    }