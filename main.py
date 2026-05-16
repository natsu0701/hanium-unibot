from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import chromadb
import uuid

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ChromaDB 클라이언트 생성
client = chromadb.PersistentClient(path="./chroma_db")

# 컬렉션 생성
collection = client.get_or_create_collection(
    name="chat_collection"
)

# 요청 모델
class ChatRequest(BaseModel):
    message: str
    user_id: str


@app.get("/")
def root():
    return {"status": "ok"}


@app.post("/api/chat")
def chat(request: ChatRequest):

    document_id = str(uuid.uuid4())

    # ChromaDB 저장
    collection.add(
        documents=[request.message],
        metadatas=[
            {
                "user_id": request.user_id
            }
        ],
        ids=[document_id]
    )

    return {
        "status": "saved",
        "document_id": document_id,
        "message": request.message
    }