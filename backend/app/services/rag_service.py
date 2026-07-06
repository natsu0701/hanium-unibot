"""
rag_service.py
Uni-Bot 프로젝트 — 유정진 담당 (RAG 파이프라인)

chunks.json을 받아서 임베딩 후 ChromaDB에 저장하고
질문을 받아서 관련 청크를 검색합니다.
"""

import json
import os
from sentence_transformers import SentenceTransformer
import chromadb

# ────────────────────────────────────────────
# 1. 모델 & ChromaDB 초기화
# ────────────────────────────────────────────

MODEL_NAME = "jhgan/ko-sroberta-multitask"
COLLECTION_NAME = "school_regulations"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "../../chroma_db")
DEFAULT_CHUNKS_PATH = os.path.join(BASE_DIR, "../../scripts/extracted.json")

model = SentenceTransformer(MODEL_NAME)
client = chromadb.PersistentClient(path=CHROMA_PATH)


# ────────────────────────────────────────────
# 2. chunks.json → ChromaDB 저장
# ────────────────────────────────────────────

def load_chunks(json_path: str) -> list:
    """chunks.json 파일 로드"""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_search_text(chunk: dict) -> str:
    """
    장 제목 + 조 제목 + 본문을 합쳐서 임베딩용 텍스트 생성
    장 번호와 절 제목 같은 메타데이터를 추가해서 정밀한 검색이 가능하도록 추가함
    예시
    -------
    "휴학·복학·제적 및 자퇴 휴학 휴학하고자 하는 사람은..."
    """
    parts = []
    if chunk.get("chapter_title"):
        parts.append(chunk["chapter_title"])
    if chunk.get("article_title"):
        parts.append(chunk["article_title"])
    parts.append(chunk["text"])
    return " ".join(parts)


def save_to_chromadb(chunks: list, reset: bool = False):
    """
    청크 리스트를 임베딩해서 ChromaDB에 저장

    Parameters
    ----------
    chunks  : chunks.json 에서 로드한 리스트
    reset   : True면 기존 컬렉션 삭제 후 새로 생성
    """

    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
            print("기존 컬렉션 삭제 완료")
        except:
            pass

    collection = client.get_or_create_collection(COLLECTION_NAME)

    # 빈 text 필터링
    chunks = [c for c in chunks if c.get("text", "").strip()]

    print(f"총 {len(chunks)}개 청크 임베딩 중...")

    # 장 제목 + 조 제목 + 본문 합쳐서 임베딩 (검색 정확도 향상)
    search_texts = [build_search_text(c) for c in chunks]
    vectors = model.encode(search_texts, batch_size=32, show_progress_bar=True).tolist()

    # 메타데이터 구성
    metadatas = []
    for c in chunks:
        meta = {
            "page":          str(c.get("page", "")),
            "doc_id":        str(c.get("doc_id", "")),
            "doc_name":      str(c.get("doc_name", "")),
            "chapter":       str(c.get("chapter", "")),
            "chapter_title": str(c.get("chapter_title", "")),
            "article":       str(c.get("article", "")),
            "article_title": str(c.get("article_title", "")),
            "is_table":      str(c.get("is_table", False)),
        }
        metadatas.append(meta)

    ids = [f"chunk_{i}" for i in range(len(chunks))]

    # documents에는 원본 text 저장 (반환용)
    # embeddings에는 메타데이터 포함 벡터 저장 (검색용)
    collection.add(
        documents=[c["text"] for c in chunks],
        embeddings=vectors,
        metadatas=metadatas,
        ids=ids
    )

    print(f"✅ ChromaDB 저장 완료: {len(chunks)}개 청크")


# ────────────────────────────────────────────
# 3. 검색
# ────────────────────────────────────────────

def search(query: str, n_results: int = 3) -> list:
    """
    질문을 받아서 관련 청크 Top-N 반환

    Parameters
    ----------
    query     : 사용자 질문
    n_results : 반환할 청크 수 (기본 3)

    Returns
    -------
    [
        {
            "text": "...",
            "page": 3,
            "doc_id": "...",
            "doc_name": "...",
            "article": "51",
            "article_title": "휴학",
            "score": 0.87
        },
        ...
    ]
    """

    collection = client.get_or_create_collection(COLLECTION_NAME)

    query_vector = model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=n_results
    )

    output = []

    for i, doc in enumerate(results["documents"][0]):
        meta = results["metadatas"][0][i]
        distance = results["distances"][0][i]

        output.append({
            "text":          doc,
            "page":          int(meta.get("page", 0)),
            "doc_id":        meta.get("doc_id", ""),
            "doc_name":      meta.get("doc_name", ""),
            "article":       meta.get("article", ""),
            "article_title": meta.get("article_title", ""),
            "score":         round(1 / (1 + abs(distance)), 4)  # 0~1 사이 유사도
        })

    return output


# ────────────────────────────────────────────
# 4. 실행 (chunks.json → ChromaDB 저장)
# ────────────────────────────────────────────

if __name__ == "__main__":
    json_path = DEFAULT_CHUNKS_PATH

    print(f"파일 로드 중: {json_path}")
    chunks = load_chunks(json_path)
    print(f"총 {len(chunks)}개 청크 로드 완료")

    save_to_chromadb(chunks, reset=True)

    # 테스트 검색
    print("\n테스트 검색: '휴학은 최대 몇 학기까지 할 수 있어?'")
    results = search("휴학은 최대 몇 학기까지 할 수 있어?")

    for i, r in enumerate(results, 1):
        print(f"\n[{i}위] score: {r['score']}")
        print(f"  조항: 제{r['article']}조 ({r['article_title']})")
        print(f"  페이지: {r['page']}")
        print(f"  내용: {r['text'][:100]}...")