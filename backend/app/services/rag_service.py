from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer

from app.Core.logger import get_logger
from app.services.synonyms import expand_query


logger = get_logger(__name__)


# =========================================================
# 기본 설정
# =========================================================

MODEL_NAME = "jhgan/ko-sroberta-multitask"
COLLECTION_NAME = "school_regulations"

# backend/app/services/rag_service.py
# parents[0] = services
# parents[1] = app
# parents[2] = backend
BACKEND_DIR = Path(__file__).resolve().parents[2]

CHROMA_PATH = BACKEND_DIR / "chroma_db"
DEFAULT_CHUNKS_PATH = (
    BACKEND_DIR
    / "data"
    / "processed"
    / "extracted.json"
)


_model: SentenceTransformer | None = None
_client: chromadb.PersistentClient | None = None


# =========================================================
# 모델 및 ChromaDB 초기화
# =========================================================

def get_model() -> SentenceTransformer:
    """
    임베딩 모델을 최초 호출 시 한 번만 로드합니다.
    """

    global _model

    if _model is None:
        logger.info(
            "[RAG] 임베딩 모델 로드 시작 | model=%s",
            MODEL_NAME,
        )

        _model = SentenceTransformer(
            MODEL_NAME
        )

        logger.info(
            "[RAG] 임베딩 모델 로드 완료 | model=%s",
            MODEL_NAME,
        )

    return _model


def get_client() -> chromadb.PersistentClient:
    """
    ChromaDB 클라이언트를 최초 호출 시 한 번만 생성합니다.
    """

    global _client

    if _client is None:
        CHROMA_PATH.mkdir(
            parents=True,
            exist_ok=True,
        )

        _client = chromadb.PersistentClient(
            path=str(CHROMA_PATH)
        )

    return _client


def get_collection():
    """
    학사 규정 전용 ChromaDB 컬렉션을 반환합니다.
    """

    return get_client().get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={
            "hnsw:space": "cosine",
        },
    )


def collection_count() -> int:
    """
    현재 ChromaDB에 저장된 청크 수를 반환합니다.
    """

    try:
        return get_collection().count()

    except Exception:
        return 0


# =========================================================
# JSON 로드 및 청크 전처리
# =========================================================

def load_chunks(
    json_path: str | Path = DEFAULT_CHUNKS_PATH,
) -> list[dict[str, Any]]:
    """
    extracted.json 파일을 읽어 청크 리스트로 반환합니다.
    """

    path = Path(json_path)

    if not path.exists():
        raise FileNotFoundError(
            f"청크 JSON 파일을 찾을 수 없습니다: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            "청크 JSON 최상위 구조는 배열이어야 합니다."
        )

    return [
        chunk
        for chunk in data
        if (
            isinstance(chunk, dict)
            and str(
                chunk.get("text") or ""
            ).strip()
        )
    ]


def build_search_text(
    chunk: dict[str, Any],
) -> str:
    """
    임베딩 검색에 사용할 문자열을 생성합니다.
    표 청크는 헤더에 의미가 집중되므로
    헤더를 별도로 강화합니다.
    """

    parts = [
        str(
            chunk.get("chapter_title") or ""
        ).strip(),
        str(
            chunk.get("article_title") or ""
        ).strip(),
    ]

    if chunk.get("is_table"):
        parts.append(
            " ".join(
                chunk.get("table_headers") or []
            )
        )

    parts.append(
        str(
            chunk.get("text") or ""
        ).strip()
    )

    return " ".join(
        part
        for part in parts
        if part
    )


def build_chunk_id(
    chunk: dict[str, Any],
) -> str:
    """
    동일 청크의 중복 저장을 막기 위해
    고정 ID를 생성합니다.
    """

    raw_value = "|".join(
        [
            str(
                chunk.get("doc_id") or ""
            ),
            str(
                chunk.get("doc_name") or ""
            ),
            str(
                chunk.get("page") or ""
            ),
            str(
                chunk.get("article") or ""
            ),
            str(
                chunk.get("text") or ""
            ),
        ]
    )

    digest = hashlib.sha1(
        raw_value.encode("utf-8")
    ).hexdigest()

    return f"chunk_{digest}"


def build_metadata(
    chunk: dict[str, Any],
) -> dict[str, str | int | bool]:
    """
    ChromaDB에 저장할 메타데이터를 구성합니다.
    """

    return {
        "page": int(
            chunk.get("page") or 0
        ),
        "doc_id": str(
            chunk.get("doc_id") or ""
        ),
        "doc_name": str(
            chunk.get("doc_name") or ""
        ),
        "school_id": str(
            chunk.get("school_id") or ""
        ),
        "chapter": str(
            chunk.get("chapter") or ""
        ),
        "chapter_title": str(
            chunk.get("chapter_title") or ""
        ),
        "article": str(
            chunk.get("article") or ""
        ),
        "article_title": str(
            chunk.get("article_title") or ""
        ),
        "is_table": bool(
            chunk.get(
                "is_table",
                False,
            )
        ),
        "table_headers": ", ".join(
            chunk.get("table_headers") or []
        ),
        "table_summary": str(
            chunk.get("table_summary") or ""
        ),
    }


# =========================================================
# ChromaDB 저장
# =========================================================

def save_to_chromadb(
    chunks: list[dict[str, Any]],
    *,
    reset: bool = False,
    batch_size: int = 64,
) -> int:
    """
    청크 목록을 임베딩한 후
    ChromaDB에 저장합니다.
    """

    valid_chunks = [
        chunk
        for chunk in chunks
        if str(
            chunk.get("text") or ""
        ).strip()
    ]

    # 동일 chunk_id가 배치 안에서 겹치면
    # ChromaDB upsert 시 DuplicateIDError가
    # 발생할 수 있으므로 미리 중복 제거
    deduped_chunks: dict[
        str,
        dict[str, Any],
    ] = {
        build_chunk_id(chunk): chunk
        for chunk in valid_chunks
    }

    valid_chunks = list(
        deduped_chunks.values()
    )

    if reset:
        try:
            get_client().delete_collection(
                COLLECTION_NAME
            )

            logger.info(
                "[INGEST] 기존 ChromaDB 컬렉션 삭제 완료"
            )

        except Exception:
            # 최초 실행 시 컬렉션이 없을 수 있음
            pass

    collection = get_collection()
    model = get_model()

    total_count = len(valid_chunks)

    if total_count == 0:
        logger.warning(
            "[INGEST] 저장할 유효 청크가 없습니다."
        )
        return 0

    logger.info(
        "[INGEST] 청크 임베딩 시작"
        " | total=%d | batch_size=%d",
        total_count,
        batch_size,
    )

    for start_index in range(
        0,
        total_count,
        batch_size,
    ):
        batch = valid_chunks[
            start_index:
            start_index + batch_size
        ]

        search_texts = [
            build_search_text(chunk)
            for chunk in batch
        ]

        vectors = model.encode(
            search_texts,
            batch_size=min(
                batch_size,
                32,
            ),
            show_progress_bar=True,
            normalize_embeddings=True,
        ).tolist()

        collection.upsert(
            ids=[
                build_chunk_id(chunk)
                for chunk in batch
            ],
            documents=[
                str(
                    chunk.get("text") or ""
                )
                for chunk in batch
            ],
            embeddings=vectors,
            metadatas=[
                build_metadata(chunk)
                for chunk in batch
            ],
        )

    logger.info(
        "[INGEST] ChromaDB 저장 완료 | total=%d",
        total_count,
    )

    return total_count


def ingest_json(
    json_path: str | Path = DEFAULT_CHUNKS_PATH,
    *,
    reset: bool = True,
) -> int:
    """
    JSON을 불러와 ChromaDB까지 적재합니다.
    """

    chunks = load_chunks(
        json_path
    )

    logger.info(
        "[INGEST] 청크 파일 로드 완료"
        " | path=%s",
        json_path,
    )

    logger.info(
        "[INGEST] 로드된 유효 청크 수: %d",
        len(chunks),
    )

    return save_to_chromadb(
        chunks,
        reset=reset,
    )


# =========================================================
# 검색 점수 보정
# =========================================================

TOKEN_PATTERN = re.compile(
    r"[가-힣A-Za-z0-9]{2,}"
)


def tokenize(
    text: str,
) -> set[str]:
    """
    질문과 문서에서 비교할 주요 단어를 추출합니다.
    """

    stopwords = {
        "무엇",
        "어떻게",
        "알려줘",
        "알려주세요",
        "관련",
        "대한",
        "있는지",
        "있나요",
        "되나요",
        "가능한가요",
        "가능해",
        "최대",
    }

    return {
        token.lower()
        for token
        in TOKEN_PATTERN.findall(text)
        if token.lower()
        not in stopwords
    }


def calculate_keyword_score(
    query: str,
    document: str,
    metadata: dict[str, Any],
) -> float:
    """
    질문 핵심어와 문서 핵심어의
    일치 비율을 계산합니다.
    """

    query_tokens = tokenize(
        query
    )

    if not query_tokens:
        return 0.0

    searchable_text = " ".join(
        [
            document,
            str(
                metadata.get(
                    "chapter_title"
                )
                or ""
            ),
            str(
                metadata.get(
                    "article_title"
                )
                or ""
            ),
        ]
    )

    document_tokens = tokenize(
        searchable_text
    )

    overlap_count = len(
        query_tokens
        & document_tokens
    )

    return (
        overlap_count
        / len(query_tokens)
    )


# =========================================================
# 청크 검색
# =========================================================

def search(
    query: str,
    n_results: int = 3,
    *,
    min_score: float = 0.20,
    school_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    사용자 질문과 관련된 청크를 반환합니다.

    검색 전에 동의어를 추가하여
    질의를 확장합니다.

    최종 점수:
    - 의미 유사도 50%
    - 키워드 일치도 50%
    """

    original_query = query.strip()

    if not original_query:
        logger.warning(
            "[SEARCH] 빈 질의가 들어와"
            " 검색을 건너뜁니다."
        )
        return []

    # -----------------------------
    # 동의어 기반 질의 확장
    # -----------------------------
    expanded_query = expand_query(
        original_query
    )

    logger.info(
        "[SEARCH] 원본 질의: %r",
        original_query,
    )

    if expanded_query != original_query:
        logger.info(
            "[SEARCH] 확장 질의: %r",
            expanded_query,
        )

    else:
        logger.info(
            "[SEARCH] 동의어 확장 없음"
        )

    query_tokens = sorted(
        tokenize(expanded_query)
    )

    logger.info(
        "[SEARCH] 추출 키워드: %s",
        query_tokens,
    )

    logger.info(
        "[SEARCH] 설정"
        " | school_id=%s"
        " | n_results=%d"
        " | min_score=%.3f",
        school_id or "미적용",
        n_results,
        min_score,
    )

    collection = get_collection()
    stored_count = collection.count()

    logger.info(
        "[SEARCH] ChromaDB 전체 청크 수: %d"
        " | school 필터: %s",
        stored_count,
        school_id or "미적용",
    )

    if stored_count == 0:
        logger.error(
            "[SEARCH] ChromaDB가 비어 있습니다."
        )

        raise RuntimeError(
            "ChromaDB가 비어 있습니다. "
            "먼저 extracted.json을 "
            "적재해야 합니다."
        )

    candidate_count = min(
        stored_count,
        max(
            n_results * 5,
            15,
        ),
    )

    logger.info(
        "[SEARCH] 후보 조회 요청:"
        " n_results=%d",
        candidate_count,
    )

    # 동의어가 붙은 질의로
    # 의미 임베딩 검색
    query_vector = (
        get_model()
        .encode(
            expanded_query,
            normalize_embeddings=True,
        )
        .tolist()
    )

    query_kwargs: dict[
        str,
        Any,
    ] = {
        "query_embeddings": [
            query_vector
        ],
        "n_results": candidate_count,
        "include": [
            "documents",
            "metadatas",
            "distances",
        ],
    }

    if school_id:
        query_kwargs["where"] = {
            "school_id": school_id,
        }

    raw_results = collection.query(
        **query_kwargs
    )

    documents = (
        raw_results.get(
            "documents"
        )
        or [[]]
    )[0]

    metadatas = (
        raw_results.get(
            "metadatas"
        )
        or [[]]
    )[0]

    distances = (
        raw_results.get(
            "distances"
        )
        or [[]]
    )[0]

    logger.info(
        "[SEARCH] ChromaDB 후보 반환:"
        " %d개",
        len(documents),
    )

    candidates: list[
        dict[str, Any]
    ] = []

    for (
        document,
        metadata,
        distance,
    ) in zip(
        documents,
        metadatas,
        distances,
    ):
        document = str(
            document or ""
        )

        metadata = (
            metadata
            or {}
        )

        # cosine distance는
        # 0에 가까울수록 유사
        semantic_score = max(
            0.0,
            min(
                1.0,
                1.0
                - float(distance),
            ),
        )

        # 키워드 점수 역시
        # 확장된 질의를 사용
        keyword_score = (
            calculate_keyword_score(
                expanded_query,
                document,
                metadata,
            )
        )

        final_score = (
            semantic_score * 0.5
            + keyword_score * 0.5
        )

        candidates.append(
            {
                "text": document,
                "page": int(
                    metadata.get(
                        "page"
                    )
                    or 0
                ),
                "doc_id": str(
                    metadata.get(
                        "doc_id"
                    )
                    or ""
                ),
                "doc_name": str(
                    metadata.get(
                        "doc_name"
                    )
                    or ""
                ),
                "school_id": str(
                    metadata.get(
                        "school_id"
                    )
                    or ""
                ),
                "chapter": str(
                    metadata.get(
                        "chapter"
                    )
                    or ""
                ),
                "chapter_title": str(
                    metadata.get(
                        "chapter_title"
                    )
                    or ""
                ),
                "article": str(
                    metadata.get(
                        "article"
                    )
                    or ""
                ),
                "article_title": str(
                    metadata.get(
                        "article_title"
                    )
                    or ""
                ),
                "is_table": bool(
                    metadata.get(
                        "is_table",
                        False,
                    )
                ),
                "score": round(
                    final_score,
                    4,
                ),
                "semantic_score": round(
                    semantic_score,
                    4,
                ),
                "keyword_score": round(
                    keyword_score,
                    4,
                ),
            }
        )

    candidates.sort(
        key=lambda item: item[
            "score"
        ],
        reverse=True,
    )

    # 상위 5개 후보만 상세 표시
    logger.info(
        "[SEARCH] ----- 상위 후보 점수 -----"
    )

    for rank, candidate in enumerate(
        candidates[:5],
        start=1,
    ):
        article = str(
            candidate["article"]
            or ""
        ).strip()

        article_title = str(
            candidate[
                "article_title"
            ]
            or ""
        ).strip()

        if article:
            article_label = (
                f"제{article}조"
            )

            if article_title:
                article_label += (
                    f"({article_title})"
                )

        else:
            article_label = (
                article_title
                or "조항 정보 없음"
            )

        logger.info(
            "[SEARCH] %d)"
            " semantic=%.3f"
            " keyword=%.3f"
            " final=%.3f"
            " | p.%s %s",
            rank,
            candidate[
                "semantic_score"
            ],
            candidate[
                "keyword_score"
            ],
            candidate["score"],
            candidate["page"]
            or "?",
            article_label,
        )

    if len(candidates) > 5:
        logger.info(
            "[SEARCH] ..."
            " (하위 %d개 생략)",
            len(candidates) - 5,
        )

    score_passed = [
        candidate
        for candidate
        in candidates
        if (
            candidate["score"]
            >= min_score
        )
    ]

    logger.info(
        "[SEARCH]"
        " min_score=%.3f"
        " 통과: %d개"
        " / 탈락: %d개",
        min_score,
        len(score_passed),
        (
            len(candidates)
            - len(score_passed)
        ),
    )

    output: list[
        dict[str, Any]
    ] = []

    seen_sources: set[
        tuple[str, str, int]
    ] = set()

    for candidate in score_passed:
        source_key = (
            candidate["doc_id"],
            candidate["article"],
            candidate["page"],
        )

        if source_key in seen_sources:
            logger.debug(
                "[SEARCH] 중복 출처 제외"
                " | p.%s %s",
                candidate["page"],
                candidate["article"]
                or "조항 정보 없음",
            )

            continue

        seen_sources.add(
            source_key
        )

        output.append(
            candidate
        )

        if len(output) >= n_results:
            break

    if not output:
        logger.warning(
            "[SEARCH] 최종 반환 결과 0개"
            " | school_id=%s"
            " | min_score=%.3f",
            school_id or "미적용",
            min_score,
        )

        return []

    final_sources = [
        "p.{} {}".format(
            item["page"] or "?",
            item["article_title"]
            or item["article"]
            or "조항 정보 없음",
        )
        for item in output
    ]

    logger.info(
        "[SEARCH] 최종 반환:"
        " %d개 (Top-%d)"
        " | %s",
        len(output),
        n_results,
        ", ".join(
            final_sources
        ),
    )

    return output


# =========================================================
# 직접 실행 테스트
# =========================================================

if __name__ == "__main__":
    test_question = (
        "수강신청 최대 학점은 "
        "몇 학점이야?"
    )

    print(
        f"\n테스트 질문: "
        f"{test_question}"
    )

    print(
        "확장 질문:",
        expand_query(
            test_question
        ),
    )

    test_results = search(
        test_question,
        n_results=5,
        min_score=0.0,
    )

    for index, result in enumerate(
        test_results,
        start=1,
    ):
        print(
            f"\n[{index}위] "
            f"점수: "
            f"{result['score']}"
        )

        print(
            f"출처: "
            f"{result['doc_name']} "
            f"{result['page']}페이지 "
            f"제{result['article']}조 "
            f"({result['article_title']})"
        )

        print(
            f"내용: "
            f"{result['text'][:180]}"
            f"..."
        )