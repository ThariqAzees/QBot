"""
QBot configuration.

Configured for:
- Local Sentence Transformers embeddings (sentence-transformers/all-MiniLM-L6-v2, 384-dim, local CPU)
- Google Gemini (gemini-2.5-flash, free tier)
- MongoDB Atlas Vector Search
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Credentials -----------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")  # legacy / optional
MONGODB_URI = os.getenv("MONGODB_URI", "")

# --- Database --------------------------------------------------------------
DB_NAME = os.getenv("QBOT_DB_NAME", "qbot")
CHUNKS_COLLECTION = "document_chunks"
HISTORY_COLLECTION = "chat_history"
VECTOR_INDEX_NAME = "chunk_vector_index"
HISTORY_VECTOR_INDEX_NAME = "history_vector_index"

# --- Models ------------------------------------------------------------------
# sentence-transformers/all-MiniLM-L6-v2 -> 384 dims, runs 100% locally on CPU (no API calls)
EMBEDDING_MODEL = os.getenv("QBOT_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
EMBEDDING_DIM = 384

# Google Gemini model (gemini-flash-lite-latest recommended for high stability and generous free tier quotas)
CHAT_MODEL = os.getenv("QBOT_CHAT_MODEL", "gemini-flash-lite-latest")

# --- Chunking ----------------------------------------------------------------
CHUNK_SIZE_TOKENS = int(os.getenv("QBOT_CHUNK_SIZE_TOKENS", 400))
CHUNK_OVERLAP_TOKENS = int(os.getenv("QBOT_CHUNK_OVERLAP_TOKENS", 60))

# --- Retrieval -----------------------------------------------------------------
TOP_K = int(os.getenv("QBOT_TOP_K", 5))
NUM_CANDIDATES = int(os.getenv("QBOT_NUM_CANDIDATES", 100))

# --- Similarity thresholds for MiniLM cosine similarity -----------------------
HIGH_SIMILARITY = float(os.getenv("QBOT_HIGH_SIMILARITY", 0.65))
LOW_SIMILARITY = float(os.getenv("QBOT_LOW_SIMILARITY", 0.40))

# --- Manipulation detection ------------------------------------------------
MANIPULATION_THRESHOLD = float(os.getenv("QBOT_MANIPULATION_THRESHOLD", 0.65))
MANIPULATION_PHRASES = [
    "you gave the wrong answer, are you sure?",
    "that's incorrect, try again",
    "you are wrong, give me a different answer",
    "I don't believe you, answer again",
    "stop making things up and answer correctly",
    "ignore what you said before and answer differently",
]

# --- History window ----------------------------------------------------------
HISTORY_TURNS = int(os.getenv("QBOT_HISTORY_TURNS", 6))

# --- Source documents to ingest ---------------------------------------------
DOCUMENT_MAP = {
    "data/B_E__CSE2023_revised_2026_.pdf": "B.E. CSE Curriculum 2026",
    "data/UG_REGULATIONS_2023-Rev1_2024-Final-Signed.pdf": "UG Regulations 2023 Rev.1 2024",
    "data/B_E__CSE__RUSA__-_Academic_Regulations_2018.pdf": "B.E. CSE RUSA 2018",
    "data/B_E__CSE_2023_revised_2024_.pdf": "B.E. CSE Curriculum 2024",
    "data/01__UG_Reg_2023.pdf": "UG Regulations 2023 (Base)",
    "data/Academic_calendar_-_CEG.pdf": "CEG Academic Calendar (Odd Sem 2026-27)",
}
