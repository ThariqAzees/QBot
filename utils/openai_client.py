"""
Compatibility bridge for QBot.

Redirects previous OpenAI calls to:
1. Local Sentence Transformers embeddings (sentence-transformers/all-MiniLM-L6-v2, 384-dim, local)
2. Google Gemini chat completion (gemini-2.5-flash / gemini-1.5-flash, free tier)
"""
from utils.embedding_client import embed_text, embed_texts, cosine_similarity
from utils.gemini_client import chat_completion, get_client as client

__all__ = ["embed_text", "embed_texts", "cosine_similarity", "chat_completion", "client"]
