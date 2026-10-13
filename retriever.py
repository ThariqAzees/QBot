"""Vector search retrieval (paper's "Retriever (MongoDB Vector Store)")."""
import config
from utils.mongo_client import chunks_collection
from utils.embedding_client import embed_text


def search(query: str, top_k: int = None, num_candidates: int = None) -> list[dict]:
    """Embeds `query` and runs an Atlas $vectorSearch against the
    document_chunks collection. Returns chunks with a similarity `score`
    (cosine, roughly 0-1), highest first."""
    top_k = top_k or config.TOP_K
    num_candidates = num_candidates or config.NUM_CANDIDATES

    return search_with_embedding(embed_text(query), top_k, num_candidates)


def search_with_embedding(query_embedding: list[float], top_k: int = None,
                           num_candidates: int = None) -> list[dict]:
    top_k = top_k or config.TOP_K
    num_candidates = num_candidates or config.NUM_CANDIDATES

    pipeline = [
        {
            "$vectorSearch": {
                "index": config.VECTOR_INDEX_NAME,
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": num_candidates,
                "limit": top_k,
            }
        },
        {
            "$project": {
                "text": 1,
                "source_document": 1,
                "page_start": 1,
                "page_end": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]
    return list(chunks_collection().aggregate(pipeline))
