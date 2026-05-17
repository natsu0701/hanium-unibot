from uuid import uuid4

import chromadb
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chroma_client = chromadb.PersistentClient(path="./chroma_db")
chat_collection = chroma_client.get_or_create_collection(name="chat_messages")


class ChatRequest(BaseModel):
    message: str
    user_id: str


@app.get("/")
def read_root():
    return {"status": "ok"}


@app.post("/api/chat")
def chat(request: ChatRequest):
    document_id = str(uuid4())
    chat_collection.add(
        ids=[document_id],
        documents=[request.message],
        metadatas=[{"user_id": request.user_id}],
    )

    return {
        "received": True,
        "message": request.message,
        "user_id": request.user_id,
        "document_id": document_id,
    }
