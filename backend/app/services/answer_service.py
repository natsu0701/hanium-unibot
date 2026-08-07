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
VERIFICATION_MODEL = os.getenv(
    "OPENAI_VERIFICATION_MODEL",
    "gpt-4o-mini",
)
def get_float_env(name: str, default: float) -> float:
    """
    환경변수 name을 float으로 읽어옵니다.
    잘못된 값이 들어오면 default를 그대로 사용합니다.
    """
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


SELF_RAG_THRESHOLD = get_float_env("SELF_RAG_THRESHOLD", 0.7)
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

VERIFICATION_SYSTEM_PROMPT = """
당신은 대학 학사규정 RAG 답변 검증기입니다.

사용자 질문, 검색 근거, 생성 답변을 검토하고 답변이 근거로 직접 뒷받침되는지 판단하세요.

판정 규칙:
1. 검색 근거에 없는 구체적 사실, 금액, 일정, 개인 결과를 답변하면 supported는 false입니다.
2. "다음 학기 등록금이 얼마인가요?"처럼 근거에 정확한 금액이 없으면 supported는 false입니다.
3. "내 성적으로 장학금을 받을 수 있나요?"처럼 개인 성적·개인 조건이 필요한 질문은 supported는 false입니다.
4. "교수님이 승인해 주실까요?"처럼 미래 개인 판단을 예측하는 질문은 supported는 false입니다.
5. 질문은 성적 정정인데 근거가 수강신청 정정에 관한 내용이면 supported는 false입니다.
6. 답변 전체가 근거에 직접 포함되거나 명확히 추론 가능할 때만 supported는 true입니다.
7. verification_score는 0.0~1.0 사이 숫자입니다.
8. 반드시 아래 JSON 객체만 반환하세요.

{
  "supported": true,
  "verification_score": 0.85,
  "reason": "근거가 질문과 답변을 직접 뒷받침함"
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
def verify_answer(
    question: str,
    search_results: list[dict[str, Any]],
    answer: str,
) -> dict[str, Any]:
    """
    질문, 검색 근거, 생성 답변이 실제로 일치하는지 검증합니다.

    반환값:
    {
        "supported": bool,
        "score": float,
    }
    """
    client = get_openai_client()

    verification_prompt = f"""
[사용자 질문]
{question}

[생성 답변]
{answer}

[검색된 문서 근거]
{build_context(search_results)}

위 답변이 검색된 문서 근거로 직접 뒷받침되는지 엄격하게 검증하세요.

판정 기준:
1. 근거에 없는 구체적인 금액, 날짜, 기준, 절차를 답변하면 supported는 false입니다.
2. "다음 학기 등록금은 얼마인가요?"처럼 근거에 정확한 금액이 없으면 supported는 false입니다.
3. "내 성적으로 장학금을 받을 수 있나요?"처럼 개인 성적이나 개인 조건이 필요한 질문은 supported는 false입니다.
4. "교수님이 승인해 주실까요?"처럼 미래의 개인 판단·예측 질문은 supported는 false입니다.
5. 질문이 성적 정정인데 근거가 수강신청 정정에 대한 것이라면 supported는 false입니다.
6. 답변의 핵심 내용이 검색 근거에 직접 포함된 경우에만 supported는 true입니다.
7. score는 답변과 근거의 일치 정도를 0.0~1.0 범위로 평가합니다.
8. 확신할 수 없으면 supported는 false로 판단합니다.

반드시 아래 JSON 객체만 반환하세요.

{{
  "supported": true,
  "score": 0.82
}}
""".strip()

    try:
        response = client.responses.create(
            model=VERIFICATION_MODEL,
            instructions=(
                "당신은 학사 규정 답변을 검증하는 "
                "엄격한 심사위원입니다. "
                "근거가 부족하거나 추측이 있으면 "
                "반드시 supported를 false로 판정하세요."
            ),
            input=verification_prompt,
            store=False,
        )

        raw_text = str(
            response.output_text or ""
        ).strip()

        if not raw_text:
            return {
                "supported": False,
                "score": 0.0,
            }

        parsed = extract_json_object(raw_text)

    except Exception as exc:
        print(f"[WARN] 답변 검증 실패: {exc}")

        # 검증에 실패하면 안전하게 답변을 거부한다.
        return {
            "supported": False,
            "score": 0.0,
        }

    raw_supported = parsed.get("supported", False)

    if isinstance(raw_supported, bool):
        supported = raw_supported
    elif isinstance(raw_supported, str):
        supported = raw_supported.strip().lower() == "true"
    else:
        supported = False

    try:
        score = float(parsed.get("score", 0.0))
    except (TypeError, ValueError):
        score = 0.0

    score = max(0.0, min(score, 1.0))

    return {
        "supported": supported,
        "score": score,
    }


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

    answer_confidence = normalize_confidence(
        parsed.get("confidence")
    )

    # --- 검증 모델로 Self-RAG 결과 받기 ---
    verification_result = verify_answer(
        question=question,
        search_results=search_results,
        answer=answer,
    )

    supported = bool(verification_result.get("supported", True))
    verification_score = normalize_confidence(
        verification_result.get("score")
    )

    threshold = SELF_RAG_THRESHOLD

    if not supported or verification_score < threshold:
        rejection_reason = "unsupported" if not supported else "low_score"

        return {
            "answer": "검색된 문서에서 답변을 뒷받침할 충분한 근거를 찾지 못했습니다.",
            "used_source_indexes": [],
            "confidence": verification_score,
            "verification_score": verification_score,
            "rejection_reason": rejection_reason,
        }

    final_confidence = (answer_confidence + verification_score) / 2

    return {
        "answer": answer,
        "used_source_indexes": used_source_indexes,
        "confidence": final_confidence,
        "verification_score": verification_score,
        "rejection_reason": None,
    }