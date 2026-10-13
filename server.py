"""
FastAPI Server for Anna University QBot.

Exposes REST endpoints for the ChatGPT-style web interface:
- GET  /api/health
- POST /api/chat
- GET  /api/conversations
- GET  /api/conversations/{conversation_id}
- DELETE /api/conversations/{conversation_id}
"""
import datetime
import json
import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import config
import history
import chatbot
from utils.mongo_client import client as get_mongo_client, history_collection, chunks_collection
from utils.gemini_client import get_client as get_gemini_client

app = FastAPI(
    title="Anna University QBot API",
    description="ChatGPT-style Backend for Anna University Regulations RAG (Gemini + Local Embeddings)",
    version="2.0.0",
)

# Enable CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LOCAL_STORE_FILE = os.path.join(os.path.dirname(__file__), "data", "conversations_store.json")


def _sanitize_mongo_error(err: Exception) -> str:
    msg = str(err)
    if "bad auth" in msg.lower() or "authentication failed" in msg.lower():
        return "Authentication failed (Code 8000). Check MongoDB username and password in .env."
    if "tls" in msg.lower() or "ssl" in msg.lower():
        return "SSL/TLS connection error. Ensure your current IP is whitelisted in Atlas Network Access."
    if "serverselectiontimeouterror" in msg.lower():
        return "Server selection timeout. Verify MongoDB cluster host and internet connection."
    return "Could not connect to MongoDB Atlas cluster."


def _load_local_store() -> Dict[str, Any]:
    if not os.path.exists(LOCAL_STORE_FILE):
        return {}
    try:
        with open(LOCAL_STORE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_local_store(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(LOCAL_STORE_FILE), exist_ok=True)
    try:
        with open(LOCAL_STORE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    except Exception:
        pass


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User question")
    conversation_id: Optional[str] = Field(None, description="Session / Conversation ID")


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: List[Dict[str, Any]]
    similarity_category: str
    related_questions: List[str]
    standalone_question: Optional[str] = None


@app.get("/api/health")
def get_health():
    """Health check endpoint: verifies MongoDB and Gemini status without exposing credentials."""
    mongo_status = {"connected": False, "error": None}
    chunks_count = 0
    history_count = 0

    try:
        m_client = get_mongo_client()
        m_client.admin.command("ping")
        mongo_status["connected"] = True
        try:
            chunks_count = chunks_collection().count_documents({})
            history_count = history_collection().count_documents({})
        except Exception:
            pass
    except Exception as exc:
        mongo_status["error"] = _sanitize_mongo_error(exc)

    gemini_status = {"configured": bool(config.GEMINI_API_KEY), "error": None}
    if not config.GEMINI_API_KEY:
        gemini_status["error"] = "GEMINI_API_KEY is not set in .env (get a free key at https://aistudio.google.com/app/apikey)"

    is_healthy = mongo_status["connected"] and gemini_status["configured"]

    return {
        "status": "ok" if is_healthy else "degraded",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "database": {
            "name": config.DB_NAME,
            "connected": mongo_status["connected"],
            "error": mongo_status["error"],
            "chunks_count": chunks_count,
            "history_count": history_count,
        },
        "gemini": {
            "configured": gemini_status["configured"],
            "model": config.CHAT_MODEL,
            "error": gemini_status["error"],
        },
        "embedding": {
            "type": "local SentenceTransformers (0 API cost)",
            "model": config.EMBEDDING_MODEL,
            "dimensions": config.EMBEDDING_DIM,
        },
        "documents": list(config.DOCUMENT_MAP.values()),
    }


@app.get("/api/conversations")
def list_conversations():
    """Returns a list of saved conversations with summaries."""
    conversations = {}

    try:
        cursor = history_collection().find({}).sort("timestamp", 1)
        for doc in cursor:
            sid = doc.get("session_id") or "default"
            if sid not in conversations:
                conversations[sid] = {
                    "id": sid,
                    "title": doc.get("question", "Conversation")[:60],
                    "created_at": doc.get("timestamp", datetime.datetime.utcnow()).isoformat() if isinstance(doc.get("timestamp"), datetime.datetime) else str(doc.get("timestamp")),
                    "updated_at": doc.get("timestamp", datetime.datetime.utcnow()).isoformat() if isinstance(doc.get("timestamp"), datetime.datetime) else str(doc.get("timestamp")),
                    "message_count": 0,
                }
            conversations[sid]["message_count"] += 2
            if isinstance(doc.get("timestamp"), datetime.datetime):
                conversations[sid]["updated_at"] = doc.get("timestamp").isoformat()
    except Exception:
        local = _load_local_store()
        for sid, conv in local.items():
            conversations[sid] = {
                "id": sid,
                "title": conv.get("title", "Conversation"),
                "created_at": conv.get("created_at"),
                "updated_at": conv.get("updated_at"),
                "message_count": len(conv.get("messages", [])),
            }

    result = list(conversations.values())
    result.sort(key=lambda c: c.get("updated_at", ""), reverse=True)
    return result


@app.get("/api/conversations/{conversation_id}")
def get_conversation(conversation_id: str):
    """Retrieve full messages for a specific conversation."""
    messages = []
    title = "Conversation"

    try:
        cursor = history_collection().find({"session_id": conversation_id}).sort("timestamp", 1)
        turns = list(cursor)
        if turns:
            title = turns[0].get("question", "Conversation")[:60]
            for t in turns:
                ts = t.get("timestamp")
                ts_str = ts.isoformat() if isinstance(ts, datetime.datetime) else str(ts)
                messages.append({
                    "role": "user",
                    "content": t.get("question", ""),
                    "timestamp": ts_str,
                })
                messages.append({
                    "role": "assistant",
                    "content": t.get("answer", ""),
                    "sources": t.get("sources", []),
                    "similarity_category": t.get("similarity_category", "medium"),
                    "timestamp": ts_str,
                })
            return {
                "id": conversation_id,
                "title": title,
                "messages": messages,
            }
    except Exception:
        pass

    local = _load_local_store()
    if conversation_id in local:
        return local[conversation_id]

    return {
        "id": conversation_id,
        "title": "New Chat",
        "messages": [],
    }


@app.delete("/api/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    """Safely delete a conversation and its turns."""
    deleted_mongo = 0
    try:
        res = history_collection().delete_many({"session_id": conversation_id})
        deleted_mongo = res.deleted_count
    except Exception:
        pass

    local = _load_local_store()
    if conversation_id in local:
        del local[conversation_id]
        _save_local_store(local)

    return {
        "status": "deleted",
        "id": conversation_id,
        "turns_removed": deleted_mongo,
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    """
    Accepts a user message and conversation ID.
    Executes the Gemini + SentenceTransformers RAG pipeline.
    """
    cleaned_message = req.message.strip()
    if not cleaned_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty or whitespace only.",
        )

    conv_id = req.conversation_id or str(uuid.uuid4())

    try:
        result = chatbot.answer(cleaned_message, session_id=conv_id, use_history=True)
    except Exception as exc:
        err_msg = str(exc)
        if "GEMINI_API_KEY is not set" in err_msg or "API_KEY_INVALID" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Google Gemini API key is missing or invalid. "
                    "Get a free API key at https://aistudio.google.com/app/apikey "
                    "and set GEMINI_API_KEY=your_key in your .env file."
                ),
            )
        if "bad auth" in err_msg or "authentication failed" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MongoDB Atlas authentication failed. Check MONGODB_URI in .env.",
            )
        if "ssl" in err_msg.lower() or "serverselectiontimeouterror" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MongoDB Atlas connection timeout. Ensure your IP is whitelisted in Atlas Network Access.",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating the answer: {err_msg}",
        )

    now_iso = datetime.datetime.utcnow().isoformat()
    local = _load_local_store()
    if conv_id not in local:
        local[conv_id] = {
            "id": conv_id,
            "title": cleaned_message[:60],
            "created_at": now_iso,
            "updated_at": now_iso,
            "messages": [],
        }
    local[conv_id]["updated_at"] = now_iso
    local[conv_id]["messages"].append({
        "role": "user",
        "content": cleaned_message,
        "timestamp": now_iso,
    })
    local[conv_id]["messages"].append({
        "role": "assistant",
        "content": result["answer"],
        "sources": result["sources"],
        "similarity_category": result["similarity_category"],
        "related_questions": result.get("related_questions", []),
        "standalone_question": result.get("standalone_question"),
        "timestamp": now_iso,
    })
    _save_local_store(local)

    return ChatResponse(
        conversation_id=conv_id,
        answer=result["answer"],
        sources=result["sources"],
        similarity_category=result["similarity_category"],
        related_questions=result.get("related_questions", []),
        standalone_question=result.get("standalone_question"),
    )
