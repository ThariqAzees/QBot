"""
Chat history persistence, mirroring the paper's "History" / "User Time
Series Collection" / "Related Questions" pieces of the data module.

Each turn is stored as one document in chat_history with the question,
its embedding, the answer, and the sources used -- so we can both (a)
replay recent turns back into the LLM prompt for context, and (b) do a
vector search over *past questions* to suggest related ones when the
current query gets a low retrieval score.
"""
import datetime

import config
from utils.mongo_client import history_collection


def get_recent_turns(session_id: str, limit: int = None) -> list[dict]:
    limit = limit or config.HISTORY_TURNS
    cursor = (
        history_collection()
        .find({"session_id": session_id})
        .sort("timestamp", -1)
        .limit(limit)
    )
    turns = list(cursor)
    turns.reverse()
    return turns


def append_turn(session_id: str, question: str, question_embedding: list[float],
                 answer: str, sources: list[dict], similarity_category: str):
    history_collection().insert_one({
        "session_id": session_id,
        "question": question,
        "question_embedding": question_embedding,
        "answer": answer,
        "sources": [
            {"source_document": s["source_document"],
             "page_start": s.get("page_start"), "page_end": s.get("page_end")}
            for s in sources
        ],
        "similarity_category": similarity_category,
        "timestamp": datetime.datetime.utcnow(),
    })


def find_related_questions(query_embedding: list[float], exclude_session: str,
                            top_k: int = 3) -> list[str]:
    """Vector search over previously asked questions (any session). Used
    when the current question scores low against the document corpus, so
    we can still point the user somewhere useful -- same idea as the
    paper's 'unclear' -> related-question suggestions flow."""
    pipeline = [
        {
            "$vectorSearch": {
                "index": config.HISTORY_VECTOR_INDEX_NAME,
                "path": "question_embedding",
                "queryVector": query_embedding,
                "numCandidates": 50,
                "limit": top_k + 1,
            }
        },
        {"$project": {"question": 1, "session_id": 1,
                       "score": {"$meta": "vectorSearchScore"}}},
    ]
    try:
        hits = list(history_collection().aggregate(pipeline))
    except Exception:
        # Index may not exist yet (e.g. no history ingested / index not
        # built) -- fail soft, related questions are a nice-to-have.
        return []
    out = []
    for h in hits:
        if h["session_id"] == exclude_session:
            continue
        out.append(h["question"])
        if len(out) >= top_k:
            break
    return out
