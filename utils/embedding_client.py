"""
Local Sentence Transformers Embedding Client.

Uses `sentence-transformers/all-MiniLM-L6-v2` locally on CPU.
Zero API calls, completely free, fast, and generates 384-dimensional embeddings.
"""
from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer

import config

_model = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(config.EMBEDDING_MODEL)
    return _model


def embed_texts(texts: List[str], batch_size: int = 32) -> List[List[float]]:
    """Generates embeddings locally for a list of texts using Sentence Transformers."""
    if not texts:
        return []
    model = get_model()
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return embeddings.tolist()


def embed_text(text: str) -> List[float]:
    """Generates a 384-dim embedding locally for a single text."""
    return embed_texts([text])[0]


def cosine_similarity(a: Union[List[float], np.ndarray], b: Union[List[float], np.ndarray]) -> float:
    """Calculates cosine similarity between two embedding vectors."""
    a, b = np.array(a), np.array(b)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)
