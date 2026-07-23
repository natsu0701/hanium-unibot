from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer


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
DEFAULT_CHUNKS_PATH = BACKEND_DIR / "data" / "processed" / "extracted.json"


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
        print(f"임베딩 모델 로드 중: {MODEL_NAME}")

        _model = SentenceTransformer(
            MODEL_NAME
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
            and str(chunk.get("text") or "").strip()
        )
    ]


def build_search_text(
    chunk: dict[str, Any],
) -> str:
    """
    임베딩 검색에 사용할 문자열을 생성합니다.
    """
    parts = [
        str(
            chunk.get("chapter_title") or ""
        ).strip(),
        str(
            chunk.get("article_title") or ""
        ).strip(),
        str(
            chunk.get("text") or ""
        ).strip(),
    ]

    return " ".join(
        part
        for part in parts
        if part
    )


def build_chunk_id(
    chunk: dict[str, Any],
) -> str:
    """
    동일 청크의 중복 저장을 막기 위해 고정 ID를 생성합니다.
    """
    raw_value = "|".join(
        [
            str(chunk.get("doc_id") or ""),
            str(chunk.get("doc_name") or ""),
            str(chunk.get("page") or ""),
            str(chunk.get("article") or ""),
            str(chunk.get("text") or ""),
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
            chunk.get("is_table", False)
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
    청크 목록을 임베딩한 후 ChromaDB에 저장합니다.
    """
    valid_chunks = [
        chunk
        for chunk in chunks
        if str(
            chunk.get("text") or ""
        ).strip()
    ]

    if reset:
        try:
            get_client().delete_collection(
                COLLECTION_NAME
            )
            print("기존 ChromaDB 컬렉션 삭제 완료")

        except Exception:
            # 최초 실행 시 컬렉션이 없을 수 있습니다.
            pass

    collection = get_collection()
    model = get_model()

    total_count = len(valid_chunks)

    if total_count == 0:
        print("저장할 유효 청크가 없습니다.")
        return 0

    print(
        f"총 {total_count}개 청크 임베딩 시작"
    )

    for start_index in range(
        0,
        total_count,
        batch_size,
    ):
        batch = valid_chunks[
            start_index:start_index + batch_size
        ]

        search_texts = [
            build_search_text(chunk)
            for chunk in batch
        ]

        vectors = model.encode(
            search_texts,
            batch_size=min(batch_size, 32),
            show_progress_bar=True,
            normalize_embeddings=True,
        ).tolist()

        collection.upsert(
            ids=[
                build_chunk_id(chunk)
                for chunk in batch
            ],
            documents=[
                str(chunk.get("text") or "")
                for chunk in batch
            ],
            embeddings=vectors,
            metadatas=[
                build_metadata(chunk)
                for chunk in batch
            ],
        )

    print(
        f"ChromaDB 저장 완료: {total_count}개"
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
    chunks = load_chunks(json_path)

    print(f"청크 파일 로드 완료: {json_path}")
    print(f"로드된 청크 수: {len(chunks)}")

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


def tokenize(text: str) -> set[str]:
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
        for token in TOKEN_PATTERN.findall(text)
        if token.lower() not in stopwords
    }


def calculate_keyword_score(
    query: str,
    document: str,
    metadata: dict[str, Any],
) -> float:
    """
    질문 핵심어와 문서 핵심어의 일치 비율을 계산합니다.
    """
    query_tokens = tokenize(query)

    if not query_tokens:
        return 0.0

    searchable_text = " ".join(
        [
            document,
            str(
                metadata.get("chapter_title") or ""
            ),
            str(
                metadata.get("article_title") or ""
            ),
        ]
    )

    document_tokens = tokenize(
        searchable_text
    )

    overlap_count = len(
        query_tokens & document_tokens
    )

    return overlap_count / len(query_tokens)


# =========================================================
# 청크 검색
# =========================================================

def search(
    query: str,
    n_results: int = 3,
    *,
    min_score: float = 0.20,
) -> list[dict[str, Any]]:
    """
    사용자 질문과 관련된 청크를 반환합니다.

    최종 점수:
    - 의미 유사도 85%
    - 키워드 일치도 15%
    """
    query = query.strip()

    if not query:
        return []

    collection = get_collection()
    stored_count = collection.count()

    if stored_count == 0:
        raise RuntimeError(
            "ChromaDB가 비어 있습니다. "
            "먼저 extracted.json을 적재해야 합니다."
        )

    candidate_count = min(
        stored_count,
        max(n_results * 5, 15),
    )

    query_vector = get_model().encode(
        query,
        normalize_embeddings=True,
    ).tolist()

    raw_results = collection.query(
        query_embeddings=[query_vector],
        n_results=candidate_count,
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    documents = (
        raw_results.get("documents")
        or [[]]
    )[0]

    metadatas = (
        raw_results.get("metadatas")
        or [[]]
    )[0]

    distances = (
        raw_results.get("distances")
        or [[]]
    )[0]

    candidates: list[dict[str, Any]] = []

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances,
    ):
        document = str(document or "")
        metadata = metadata or {}

        # cosine distance는 0에 가까울수록 유사합니다.
        semantic_score = max(
            0.0,
            min(
                1.0,
                1.0 - float(distance),
            ),
        )

        keyword_score = calculate_keyword_score(
            query,
            document,
            metadata,
        )

        final_score = (
            semantic_score * 0.85
            + keyword_score * 0.15
        )

        candidates.append(
            {
                "text": document,
                "page": int(
                    metadata.get("page") or 0
                ),
                "doc_id": str(
                    metadata.get("doc_id") or ""
                ),
                "doc_name": str(
                    metadata.get("doc_name") or ""
                ),
                "chapter": str(
                    metadata.get("chapter") or ""
                ),
                "chapter_title": str(
                    metadata.get("chapter_title") or ""
                ),
                "article": str(
                    metadata.get("article") or ""
                ),
                "article_title": str(
                    metadata.get("article_title") or ""
                ),
                "is_table": bool(
                    metadata.get("is_table", False)
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
        key=lambda item: item["score"],
        reverse=True,
    )

    output: list[dict[str, Any]] = []

    seen_sources: set[
        tuple[str, str, int]
    ] = set()

    for candidate in candidates:
        if candidate["score"] < min_score:
            continue

        source_key = (
            candidate["doc_id"],
            candidate["article"],
            candidate["page"],
        )

        if source_key in seen_sources:
            continue

        seen_sources.add(source_key)
        output.append(candidate)

        if len(output) >= n_results:
            break

    return output


# =========================================================
# 직접 실행 테스트
# =========================================================

if __name__ == "__main__":
    inserted_count = ingest_json(
        DEFAULT_CHUNKS_PATH,
        reset=True,
    )

    print(
        f"\n총 {inserted_count}개 청크 적재 완료"
    )

    test_question = (
        "휴학은 최대 몇 학기까지 할 수 있어?"
    )

    print(
        f"\n테스트 질문: {test_question}"
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
            f"점수: {result['score']}"
        )

        print(
            f"출처: {result['doc_name']} "
            f"{result['page']}페이지 "
            f"제{result['article']}조 "
            f"({result['article_title']})"
        )

        print(
            f"내용: {result['text'][:180]}..."
        )
