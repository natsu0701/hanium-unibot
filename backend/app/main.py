import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import chromadb
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Uni-Bot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chroma_path = Path(os.getenv("LOCALAPPDATA", Path.home())) / "UniBot" / "chroma_db"
chroma_path.mkdir(parents=True, exist_ok=True)

chroma_client = chromadb.PersistentClient(path=str(chroma_path))
chat_collection = chroma_client.get_or_create_collection(name="chat_messages")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    user_id: str
    conversation_id: UUID | None = None


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@app.get("/health")
def health():
    return {
        "data": {
            "status": "ok",
            "version": "1.0.0",
            "timestamp": utc_now(),
        },
        "request_id": f"req_{uuid4().hex}",
    }


@app.get("/")
def read_root():
    return health()


@app.post("/api/chat")
def chat(request: ChatRequest):
    message_id = f"msg_{uuid4().hex}"
    conversation_id = request.conversation_id or uuid4()

    chat_collection.add(
        ids=[message_id],
        documents=[request.message],
        embeddings=[[0.0] * 384],
        metadatas=[{"user_id": request.user_id}],
    )

    return {
        "data": {
            "answer": "관련 규정을 확인하고 있습니다. 현재는 API 연동 테스트 응답입니다.",
            "sources": [],
            "confidence": 0.0,
            "conversation_id": str(conversation_id),
            "message_id": message_id,
            "created_at": utc_now(),
        },
        "request_id": f"req_{uuid4().hex}",
    }
