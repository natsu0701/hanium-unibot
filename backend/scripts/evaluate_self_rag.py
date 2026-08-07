from __future__ import annotations

import csv
from pathlib import Path
from statistics import mean
from time import sleep
from typing import Any

import requests

API_URL = "http://127.0.0.1:8000/api/chat"
TESTSET_PATH = Path("evaluation/self_rag_testset.csv")
RESULT_PATH = Path("evaluation/self_rag_result.csv")

USER_ID = "self-rag-evaluator"
REQUEST_DELAY_SECONDS = 0.3


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def call_chat_api(question: str) -> dict[str, Any]:
    response = requests.post(
        API_URL,
        json={
            "message": question,
            "user_id": USER_ID,
        },
        timeout=60,
    )

    response.raise_for_status()

    body = response.json()
    data = body.get("data", body)

    if not isinstance(data, dict):
        raise ValueError("API 응답의 data 형식이 올바르지 않습니다.")

    return data


def classify_result(rejection_reason: str | None) -> str:
    if rejection_reason == "unsupported":
        return "unsupported"

    if rejection_reason == "low_score":
        return "low_score"

    return "normal_answer"


def main() -> None:
    if not TESTSET_PATH.exists():
        raise FileNotFoundError(
            f"테스트셋 파일을 찾을 수 없습니다: {TESTSET_PATH}"
        )

    results: list[dict[str, str]] = []
    verification_scores: list[float] = []

    with TESTSET_PATH.open(
        encoding="utf-8-sig",
        newline="",
    ) as file:
        test_cases = list(csv.DictReader(file))

    if not test_cases:
        raise ValueError(
            "self_rag_testset.csv에 질문이 없습니다."
        )

    for row in test_cases:
        question_id = str(row.get("id") or "").strip()
        question = str(row.get("question") or "").strip()

        if not question:
            results.append({
                "id": question_id,
                "question": "",
                "result_type": "api_error",
                "rejection_reason": "api_error",
                "verification_score": "",
                "answer": "질문이 비어 있습니다.",
                "status": "error",
            })
            continue

        try:
            data = call_chat_api(question)

            answer = str(data.get("answer") or "").strip()

            verification_score = to_float(
                data.get(
                    "verification_score",
                    data.get("confidence", 0.0),
                )
            )

            rejection_reason_raw = data.get(
                "rejection_reason"
            )

            rejection_reason = (
                str(rejection_reason_raw).strip()
                if rejection_reason_raw is not None
                else None
            )

            result_type = classify_result(
                rejection_reason
            )

            verification_scores.append(
                verification_score
            )

            results.append({
                "id": question_id,
                "question": question,
                "result_type": result_type,
                "rejection_reason": (
                    rejection_reason or "none"
                ),
                "verification_score": (
                    f"{verification_score:.4f}"
                ),
                "answer": answer,
                "status": "success",
            })

        except Exception as error:
            results.append({
                "id": question_id,
                "question": question,
                "result_type": "api_error",
                "rejection_reason": "api_error",
                "verification_score": "",
                "answer": str(error),
                "status": "error",
            })

        sleep(REQUEST_DELAY_SECONDS)

    RESULT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "id",
        "question",
        "result_type",
        "rejection_reason",
        "verification_score",
        "answer",
        "status",
    ]

    with RESULT_PATH.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(results)

    successful_results = [
        item
        for item in results
        if item["status"] == "success"
    ]

    total_questions = len(results)

    normal_answer_count = sum(
        item["result_type"] == "normal_answer"
        for item in successful_results
    )

    unsupported_count = sum(
        item["result_type"] == "unsupported"
        for item in successful_results
    )

    low_score_count = sum(
        item["result_type"] == "low_score"
        for item in successful_results
    )

    rejected_answer_count = (
        unsupported_count
        + low_score_count
    )

    api_error_count = sum(
        item["status"] == "error"
        for item in results
    )

    refusal_rate = (
        rejected_answer_count / total_questions * 100
        if total_questions > 0
        else 0.0
    )

    average_verification_score = (
        mean(verification_scores)
        if verification_scores
        else 0.0
    )

    print("\n========== Task 4-2 Self-RAG 평가 결과 ==========")
    print(f"전체 질문 수: {total_questions}")
    print(f"정상 답변 수: {normal_answer_count}")
    print(f"거부 답변 수: {rejected_answer_count}")
    print(f"unsupported 수: {unsupported_count}")
    print(f"low_score 수: {low_score_count}")
    print(f"답변 거부율: {refusal_rate:.1f}%")
    print(
        "평균 verification_score: "
        f"{average_verification_score:.4f}"
    )
    print(f"API 오류 수: {api_error_count}")
    print(f"상세 결과 CSV: {RESULT_PATH}")


if __name__ == "__main__":
    main()