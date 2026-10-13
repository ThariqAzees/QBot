"""
QBot core pipeline (mirrors Fig. 1 of the paper):

    user question + chat history
        -> standalone question (LLM rewrite, so retrieval isn't confused
           by pronouns like "what about semester 5?")
        -> embed -> vector search over document_chunks
        -> build prompt from retrieved chunks + recent history
        -> LLM answer
        -> classify similarity (High/Medium/Low) from top retrieval score
        -> if Low, surface related past questions
        -> persist the turn to chat_history
"""
import config
import history
import retriever
from utils.embedding_client import cosine_similarity, embed_text, embed_texts
from utils.gemini_client import chat_completion

SYSTEM_PROMPT = """You are QBot, an assistant that answers questions about \
Anna University B.E./B.Tech academic regulations, curricula, and the CEG \
academic calendar, using ONLY the provided context excerpts.

Rules:
- Answer using only the CONTEXT below. If the context doesn't contain the \
answer, say you don't have enough information in the ingested documents \
rather than guessing.
- When regulations differ by year/version (e.g. 2018 RUSA vs 2023 vs 2024 \
vs 2026 curriculum), be explicit about which document/version your answer \
comes from.
- Cite the source document and page(s) inline, e.g. (UG Regulations 2023 \
Rev.1 2024, p. 12).
- Be concise and precise -- these are policy/procedural questions where \
exact numbers (credits, percentages, CGPA cutoffs, days) matter.
"""

REWRITE_PROMPT = """Given the chat history and a follow-up question, \
rewrite the follow-up into a standalone question that contains all \
necessary context and can be understood without the chat history. Do not \
answer it -- only rewrite it. If it is already standalone, return it \
unchanged."""


def _classify_similarity(top_score: float) -> str:
    if top_score >= config.HIGH_SIMILARITY:
        return "high"
    if top_score >= config.LOW_SIMILARITY:
        return "medium"
    return "low"


def _detect_manipulation(question_embedding: list[float]) -> bool:
    phrase_embeddings = embed_texts(config.MANIPULATION_PHRASES)
    best = max(cosine_similarity(question_embedding, pe) for pe in phrase_embeddings)
    return best >= config.MANIPULATION_THRESHOLD


def _rewrite_standalone(question: str, turns: list[dict]) -> str:
    if not turns:
        return question
    history_text = "\n".join(
        f"User: {t['question']}\nQBot: {t['answer']}" for t in turns
    )
    messages = [
        {"role": "system", "content": REWRITE_PROMPT},
        {"role": "user", "content": f"Chat history:\n{history_text}\n\n"
                                     f"Follow-up question: {question}\n\n"
                                     f"Standalone question:"},
    ]
    return chat_completion(messages, temperature=0.0)


def _build_context(chunks: list[dict]) -> str:
    parts = []
    for c in chunks:
        pages = f"p. {c['page_start']}" if c["page_start"] == c["page_end"] \
            else f"pp. {c['page_start']}-{c['page_end']}"
        parts.append(f"[{c['source_document']}, {pages}]\n{c['text']}")
    return "\n\n---\n\n".join(parts)


def answer(question: str, session_id: str = "default", use_history: bool = True):
    turns = history.get_recent_turns(session_id) if use_history else []

    question_embedding = embed_text(question)
    if _detect_manipulation(question_embedding):
        return {
            "answer": ("I want to make sure I answer what you actually need -- "
                       "could you tell me specifically what seemed wrong or "
                       "which part you'd like me to re-check?"),
            "sources": [],
            "similarity_category": "manipulation_flagged",
            "related_questions": [],
        }

    standalone_q = _rewrite_standalone(question, turns)
    q_embedding = embed_text(standalone_q) if standalone_q != question else question_embedding

    hits = retriever.search_with_embedding(q_embedding)
    top_score = hits[0]["score"] if hits else 0.0
    category = _classify_similarity(top_score)

    context = _build_context(hits)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for t in turns:
        messages.append({"role": "user", "content": t["question"]})
        messages.append({"role": "assistant", "content": t["answer"]})
    messages.append({
        "role": "user",
        "content": f"CONTEXT:\n{context}\n\nQUESTION: {standalone_q}",
    })

    answer_text = chat_completion(messages)

    related = []
    if category == "low":
        related = history.find_related_questions(q_embedding, exclude_session=session_id)

    history.append_turn(session_id, question, question_embedding, answer_text,
                         hits, category)

    return {
        "answer": answer_text,
        "sources": [
            {"source_document": h["source_document"],
             "page_start": h["page_start"], "page_end": h["page_end"],
             "score": round(h["score"], 4)}
            for h in hits
        ],
        "similarity_category": category,
        "related_questions": related,
        "standalone_question": standalone_q,
    }
