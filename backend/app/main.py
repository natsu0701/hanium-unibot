from __future__ import annotations

import json
import re
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]  # backend 폴더
load_dotenv(BASE_DIR / ".env")

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import BACKEND_DIR, Base, SessionLocal, engine, get_db
from app.models import ChatLog, Document
from app.services.answer_service import generate_answer
from app.services.rag_service import (
    DEFAULT_CHUNKS_PATH,
    collection_count,
    ingest_json,
    search,
    get_model,  # warm-up용으로 추가
)


RAW_DIR = BACKEND_DIR / "data" / "raw"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
UPLOAD_CHUNK_SIZE = 1024 * 1024


# =========================================================
# 공통 함수
# =========================================================

def utc_now() -> str:
    """현재 UTC 시간을 ISO 형식 문자열로 반환합니다."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def format_utc(value: datetime) -> str:
    """datetime을 UTC ISO 문자열로 변환합니다."""
    if value.tzinfo is None:
        return value.isoformat() + "Z"

    return value.isoformat().replace("+00:00", "Z")


def document_to_dict(document: Document) -> dict:
    """Document ORM 객체를 API 응답 형식으로 변환합니다."""
    return {
        "id": document.id,
        "filename": document.filename,
        "size_bytes": document.size_bytes,
        "status": document.status,
        "chunks_count": document.chunks_count,
        "upload_time": format_utc(document.upload_time),
    }


def process_document(doc_id: str) -> None:
    """
    업로드된 PDF 처리 파이프라인 자리표시자입니다.

    W4 후반에 예진님 OCR/청킹 파이프라인으로 교체합니다.
    """
    db = SessionLocal()

    try:
        document = (
            db.query(Document)
            .filter(Document.id == doc_id)
            .first()
        )

        if document is None:
            return

        document.status = "processing"
        db.commit()

        time.sleep(5)

        document.status = "completed"
        db.commit()

    except Exception as exc:
        db.rollback()
        print(
            f"문서 처리 중 오류 발생 ({doc_id}): {exc}"
        )

    finally:
        db.close()


def clean_text(text: str) -> str:
    """불필요한 공백과 줄바꿈을 정리합니다."""
    return re.sub(r"\s+", " ", text).strip()


def make_excerpt(
    text: str,
    max_length: int = 300,
) -> str:
    """검색된 청크 원문을 지정한 길이로 줄여 반환합니다."""
    cleaned = clean_text(text)

    if len(cleaned) <= max_length:
        return cleaned

    return cleaned[:max_length].rstrip() + "…"


def build_source_text(result: dict) -> str:
    """
    프론트 SourceChip에서 표시할 source.text를 생성합니다.

    예:
    guide.pdf · 21페이지 · 제48조 (휴학)
    """
    parts: list[str] = []

    doc_name = str(
        result.get("doc_name") or ""
    ).strip()

    page = result.get("page")

    article = str(
        result.get("article") or ""
    ).strip()

    article_title = str(
        result.get("article_title") or ""
    ).strip()

    if doc_name:
        parts.append(doc_name)

    if page:
        parts.append(f"{page}페이지")

    if article:
        normalized_article = article

        if not normalized_article.startswith("제"):
            normalized_article = f"제{normalized_article}"

        if not normalized_article.endswith("조"):
            normalized_article = f"{normalized_article}조"

        if article_title:
            normalized_article += f" ({article_title})"

        parts.append(normalized_article)

    return " · ".join(parts) if parts else "근거 보기"


def source_from_result(result: dict) -> dict:
    """
    프론트와 호환되는 출처 데이터를 생성합니다.

    프론트에서 사용하는 주요 필드:
    - source.text
    - source.page
    - source.evidence
    """
    return {
        "text": build_source_text(result),
        "page": int(
            result.get("page") or 0
        ),

        # 상세 출처 표시 및 향후 확장용
        "doc_id": str(
            result.get("doc_id") or ""
        ),
        "doc_name": str(
            result.get("doc_name") or ""
        ),
        "chapter": str(
            result.get("chapter") or ""
        ),
        "chapter_title": str(
            result.get("chapter_title") or ""
        ),
        "article": str(
            result.get("article") or ""
        ),
        "article_title": str(
            result.get("article_title") or ""
        ),
        "is_table": bool(
            result.get("is_table", False)
        ),
        "score": float(
            result.get("score") or 0.0
        ),
        "evidence": make_excerpt(
            str(result.get("text") or ""),
            max_length=400,
        ),
    }


def save_chat_log(
    *,
    user_id: str,
    conversation_id: str,
    user_message: str,
    bot_answer: str,
    confidence: float,
    sources: list[dict],
) -> None:
    """
    최종 채팅 결과를 SQLite chat_logs 테이블에 저장합니다.
    """
    db = SessionLocal()

    try:
        chat_log = ChatLog(
            user_id=user_id,
            conversation_id=conversation_id,
            user_message=user_message,
            bot_answer=bot_answer,
            confidence=confidence,
            sources_json=json.dumps(
                sources,
                ensure_ascii=False,
            ),
        )

        db.add(chat_log)

         #테스트용: 항상 실패를 발생시키기
         #raise RuntimeError("테스트용 강제 채팅 로그 저장 실패")
    
        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# =========================================================
# 서버 시작 처리
# =========================================================

@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    서버 시작 시 다음 작업을 수행합니다.

    1. SQLite 테이블 생성
    2. 임베딩 모델 warm-up
    3. ChromaDB 데이터 상태 확인
    4. ChromaDB가 비어 있으면 processed JSON 자동 적재
    """

    # SQLite 테이블을 생성합니다.
    try:
        Base.metadata.create_all(
            bind=engine
        )
        
        print(
            "[INFO] SQLite 테이블 초기화 완료"
        )

    except Exception as exc:
        print(
            f"[ERROR] SQLite 초기화 중 오류 발생: {exc}"
        )
     # 임베딩 모델 warm-up
    try:
        print("[INFO]임베딩 모델 warm-up 시작...")
        get_model()  # rag_service의 임베딩 모델을 미리 로드
        print("[INFO]임베딩 모델 준비 완료")
    except Exception as exc:
        print(f"[ERROR]임베딩 모델 warm-up 중 오류 발생: {exc}")

    # ChromaDB를 확인합니다.
    try:
        current_count = collection_count()

        if current_count == 0:
            if DEFAULT_CHUNKS_PATH.exists():
                print(
                    "[INFO]ChromaDB가 비어 있어 데이터를 적재합니다: "
                    f"{DEFAULT_CHUNKS_PATH}"
                )

                inserted_count = ingest_json(
                    DEFAULT_CHUNKS_PATH,
                    reset=True,
                )

                print(
                    "[INFO]ChromaDB 데이터 적재 완료: "
                    f"{inserted_count}개"
                )

            else:
                print(
                    "[WARN]청크 JSON 파일을 찾을 수 없습니다. "
                    f"경로: {DEFAULT_CHUNKS_PATH}"
                )

        else:
            print(
                "[INFO]기존 ChromaDB 데이터를 사용합니다: "
                f"{current_count}개"
            )

    except Exception as exc:
        # RAG 초기화가 실패하더라도 서버 상태 확인은
        # 가능하도록 서버 전체 실행은 유지합니다.
        print(
            f"[ERROR]RAG 초기화 중 오류 발생: {exc}"
        )

    yield


# =========================================================
# FastAPI 설정
# =========================================================

app = FastAPI(
    title="Uni-Bot API",
    description=(
        "대학 학사 문서를 검색하고 OpenAI를 통해 "
        "근거 기반 답변을 생성하는 Uni-Bot API"
    ),
    version="1.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# 요청 스키마
# =========================================================

class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=2000,
        description="사용자가 입력한 학사 관련 질문",
    )

    user_id: str = Field(
        default="anonymous",
        min_length=1,
        max_length=100,
        description="사용자 식별값",
    )

    conversation_id: UUID | None = Field(
        default=None,
        description="기존 대화 식별값",
    )


class SearchRequest(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=2000,
        description="검색할 질문 또는 핵심어",
    )

    n_results: int = Field(
        default=5,
        ge=1,
        le=10,
        description="반환할 검색 결과 수",
    )


# =========================================================
# 기본 API
# =========================================================

@app.get("/health")
def health():
    """서버, RAG 데이터, SQLite 상태를 확인합니다."""
    try:
        rag_chunk_count = collection_count()

    except Exception:
        rag_chunk_count = 0

    return {
        "data": {
            "status": "ok",
            "version": app.version,
            "rag_chunk_count": rag_chunk_count,
            "openai_rag_enabled": True,
            "chat_history_enabled": True,
            "timestamp": utc_now(),
        },
        "request_id": f"req_{uuid4().hex}",
    }


@app.get("/")
def read_root():
    """기본 서버 상태를 반환합니다."""
    return health()


# =========================================================
# 검색 테스트 API
# =========================================================

@app.post("/api/search")
def search_api(request: SearchRequest):
    """
    OpenAI 답변 생성 없이 ChromaDB 검색 결과만 확인합니다.

    검색 정확도와 청크 내용을 점검할 때 사용하는 테스트 API입니다.
    """
    try:
        results = search(
            request.query,
            n_results=request.n_results,
            min_score=0.0,
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"검색 중 오류가 발생했습니다: {exc}",
        ) from exc

    return {
        "data": {
            "query": request.query,
            "count": len(results),
            "results": results,
        },
        "request_id": f"req_{uuid4().hex}",
    }


# =========================================================
# OpenAI 기반 RAG 채팅 API
# =========================================================

@app.post("/api/chat")
def chat(request: ChatRequest):
    """
    프론트 채팅창에서 호출하는 OpenAI 기반 RAG 채팅 API입니다.

    처리 순서:
    1. 사용자 질문으로 ChromaDB 검색
    2. 관련 청크 Top-3 조회
    3. 검색 결과를 OpenAI에 전달
    4. 질문에 필요한 내용만 요약한 답변 생성
    5. 실제로 사용한 출처만 선택
    6. 최종 질문·답변·출처를 SQLite에 저장
    """
    message_id = f"msg_{uuid4().hex}"
    conversation_id = (
        request.conversation_id
        or uuid4()
    )
    request_id = f"req_{uuid4().hex}"
    rejection_reason: str | None = None  # 미리 초기화 추가
    try:
        # 1. 질문과 관련된 문서 청크를 검색합니다.
        search_results = search(
            request.message,
            n_results=3,
            min_score=0.20,
        )
    
        # 2. 검색 결과를 OpenAI에 전달해
        # 최종 답변을 생성합니다.
        generated = generate_answer(
            question=request.message,
            search_results=search_results,
        )
        

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"답변 생성 중 오류가 발생했습니다: {exc}",
        ) from exc

    # OpenAI가 실제 답변 작성에 사용했다고 선택한
    # 검색 결과 번호입니다.
    used_indexes = generated.get(
        "used_source_indexes",
        [],
    )

    if not isinstance(used_indexes, list):
        used_indexes = []

    valid_used_indexes: list[int] = []

    for index in used_indexes:
        if (
            isinstance(index, int)
            and 0 <= index < len(search_results)
            and index not in valid_used_indexes
        ):
            valid_used_indexes.append(index)

    # 실제 답변 작성에 사용한 검색 결과만 선택합니다.
    used_results = [
        search_results[index]
        for index in valid_used_indexes
    ]

    # 프론트에서 사용하는 출처 형식으로 변환합니다.
    sources = [
        source_from_result(result)
        for result in used_results
    ]

    answer = str(
        generated.get("answer")
        or "답변을 생성하지 못했습니다."
    ).strip()
    # 새로 추가: rejection_reason 읽기
    rejection_reason = generated.get("rejection_reason")

    try:
        confidence = float(
            generated.get(
                "confidence",
                0.0,
            )
        )

    except (TypeError, ValueError):
        confidence = 0.0

    confidence = max(
        0.0,
        min(confidence, 1.0),
    )
    try:
        verification_score = float(
            generated.get(
                "verification_score",
                confidence,
            )
        )
    except (TypeError, ValueError):
        verification_score = confidence

    verification_score = max(
        0.0,
        min(verification_score, 1.0),
    )

    # 최종 채팅 결과를 SQLite에 저장합니다.
    try:
        save_chat_log(
            user_id=request.user_id,
            conversation_id=str(
                conversation_id
            ),
            user_message=request.message,
            bot_answer=answer,
            confidence=confidence,
            sources=sources,
        )

    except Exception as exc:
        # 로그 저장 실패는 사용자 응답에 영향을 주지 않고,
        # 서버 콘솔에만 경고로 남깁니다.
        print(
            f"[WARN]경고: 채팅 이력 저장 실패 (사용자에게는 답변 정상 반환): {exc}"
        )

    created_at = utc_now()

    return {
    "data": {
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
        "verification_score": verification_score,
        "rejection_reason": rejection_reason,
        "conversation_id": str(conversation_id),
        "message_id": message_id,
        "created_at": created_at,
    },
    "request_id": request_id,
}


# =========================================================
# 채팅 이력 조회 API
# =========================================================

@app.get("/api/chat/history")
def chat_history(
    user_id: str = Query(
        ...,
        min_length=1,
        max_length=100,
        description="조회할 사용자 식별값",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="반환할 최대 이력 수",
    ),
    page: int = Query(
        default=1,
        ge=1,
        description="조회할 페이지 번호 (1부터 시작)",
    ),
    conversation_id: UUID | None = Query(
        default=None,
        description="특정 대화만 필터링할 경우 사용",
    ),
    db: Session = Depends(get_db),
):
    """
    /api/chat에서 SQLite에 저장된 채팅 이력을 조회합니다.

    created_at 역순(최신순)으로 정렬하여 반환합니다.
    """
    try:
        query = db.query(ChatLog).filter(
            ChatLog.user_id == user_id
        )

        if conversation_id is not None:
            query = query.filter(
                ChatLog.conversation_id
                == str(conversation_id)
            )
        
        total_count = query.count()

        offset = (page - 1) * limit
        
        chat_logs = (
            query
            .order_by(ChatLog.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "채팅 이력 조회 중 오류가 발생했습니다: "
                f"{exc}"
            ),
        ) from exc

    items = []

    for chat_log in chat_logs:
        try:
            sources = json.loads(
                chat_log.sources_json
            )

        except (TypeError, json.JSONDecodeError):
            sources = []

        if not isinstance(sources, list):
            sources = []

        created_at = chat_log.created_at

        if created_at.tzinfo is None:
            created_at_str = (
                created_at.isoformat() + "Z"
            )
        else:
            created_at_str = (
                created_at
                .isoformat()
                .replace("+00:00", "Z")
            )

        items.append(
            {
                "id": chat_log.id,
                "user_message": chat_log.user_message,
                "bot_answer": chat_log.bot_answer,
                "confidence": chat_log.confidence,
                "sources": sources,
                "created_at": created_at_str,
            }
        )

    has_more = offset + len(items) < total_count

    return {
        "data": {
            "count": len(items),
            "items": items,
            "has_more": has_more,
        },
        "request_id": f"req_{uuid4().hex}",
    }


# =========================================================
# PDF 문서 업로드 / 목록 API
# =========================================================

@app.post(
    "/api/documents",
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    PDF 문서를 업로드하고 처리 파이프라인을 백그라운드에서 시작합니다.
    """
    original_filename = (
        file.filename or ""
    ).strip()

    content_type = (
        file.content_type or ""
    ).lower()

    is_pdf_name = original_filename.lower().endswith(
        ".pdf"
    )
    is_pdf_type = content_type in {
        "application/pdf",
        "application/x-pdf",
    }

    if not (is_pdf_name or is_pdf_type):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": "PDF 파일만 업로드할 수 있습니다.",
            },
        )

    doc_id = str(uuid4())
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    save_path = RAW_DIR / f"{doc_id}.pdf"

    size_bytes = 0

    try:
        with save_path.open("wb") as output:
            while True:
                chunk = await file.read(
                    UPLOAD_CHUNK_SIZE
                )

                if not chunk:
                    break

                size_bytes += len(chunk)

                if size_bytes > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail={
                            "code": "FILE_TOO_LARGE",
                            "message": (
                                "파일 크기는 50MB를 "
                                "초과할 수 없습니다."
                            ),
                        },
                    )

                output.write(chunk)

    except HTTPException:
        if save_path.exists():
            save_path.unlink()

        raise

    except Exception as exc:
        if save_path.exists():
            save_path.unlink()

        raise HTTPException(
            status_code=500,
            detail=(
                "파일 저장 중 오류가 발생했습니다: "
                f"{exc}"
            ),
        ) from exc

    finally:
        await file.close()

    if size_bytes == 0:
        if save_path.exists():
            save_path.unlink()

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": "빈 파일은 업로드할 수 없습니다.",
            },
        )

    filename = (
        Path(original_filename).name
        if original_filename
        else f"{doc_id}.pdf"
    )

    if not filename.lower().endswith(".pdf"):
        filename = f"{filename}.pdf"

    document = Document(
        id=doc_id,
        filename=filename,
        size_bytes=size_bytes,
        status="pending",
        chunks_count=None,
    )

    try:
        db.add(document)
        db.commit()
        db.refresh(document)

    except Exception as exc:
        db.rollback()

        if save_path.exists():
            save_path.unlink()

        raise HTTPException(
            status_code=500,
            detail=(
                "문서 메타데이터 저장 중 오류가 "
                f"발생했습니다: {exc}"
            ),
        ) from exc

    background_tasks.add_task(
        process_document,
        doc_id,
    )

    return {
        "data": document_to_dict(document),
        "request_id": f"req_{uuid4().hex}",
    }


@app.get("/api/documents")
def list_documents(
    db: Session = Depends(get_db),
):
    """업로드된 문서를 upload_time 역순으로 조회합니다."""
    try:
        documents = (
            db.query(Document)
            .order_by(Document.upload_time.desc())
            .all()
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "문서 목록 조회 중 오류가 발생했습니다: "
                f"{exc}"
            ),
        ) from exc

    items = [
        document_to_dict(document)
        for document in documents
    ]

    return {
        "data": {
            "count": len(items),
            "items": items,
        },
        "request_id": f"req_{uuid4().hex}",
    }