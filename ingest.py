"""
Ingestion pipeline (paper's "Data Module" + "Vector Operations Module"):

    PDF files -> per-page text (OCR fallback for scans)
              -> overlapping token-window chunks
              -> OpenAI embeddings (text-embedding-3-small, 1536-dim)
              -> upserted into MongoDB Atlas (document_chunks collection)

Run:
    python ingest.py                 # ingest every doc in config.DOCUMENT_MAP
    python ingest.py --only "B.E. CSE RUSA 2018"   # just one document
    python ingest.py --skip-index    # skip the vector search index step
"""
import argparse
import hashlib
import os
import sys

from pymongo import UpdateOne

import config
from utils.chunking import chunk_document
from utils.mongo_client import chunks_collection, db
from utils.embedding_client import embed_texts
from utils.pdf_extract import extract_pages


def _chunk_id(source_document: str, chunk_index: int) -> str:
    raw = f"{source_document}::{chunk_index}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def ingest_document(pdf_path: str, source_document: str) -> int:
    if not os.path.exists(pdf_path):
        print(f"  [skip] {pdf_path} not found")
        return 0

    print(f"-> {source_document}  ({pdf_path})")
    pages = extract_pages(pdf_path)
    print(f"   extracted text from {len(pages)} page(s)")

    chunks = chunk_document(
        pages, source_document,
        chunk_size=config.CHUNK_SIZE_TOKENS,
        overlap=config.CHUNK_OVERLAP_TOKENS,
    )
    print(f"   built {len(chunks)} chunk(s)")
    if not chunks:
        return 0

    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)

    ops = []
    for c, emb in zip(chunks, embeddings):
        doc_id = _chunk_id(source_document, c["chunk_index"])
        doc = {**c, "_id": doc_id, "embedding": emb}
        ops.append(UpdateOne({"_id": doc_id}, {"$set": doc}, upsert=True))

    result = chunks_collection().bulk_write(ops)
    print(f"   upserted {result.upserted_count} new / "
          f"{result.modified_count} updated chunks")
    return len(chunks)


def ensure_vector_index():
    """Best-effort creation of the Atlas Vector Search index. This requires
    an Atlas cluster (free M0 tier is fine) -- it will not work against a
    plain self-hosted mongod. If it fails (e.g. index already exists, or
    your driver/server version doesn't support create_search_index), the
    manual index definition is printed so you can paste it into the Atlas
    UI (Atlas > your cluster > Search > Create Search Index > JSON Editor)."""
    index_def = {
        "name": config.VECTOR_INDEX_NAME,
        "type": "vectorSearch",
        "definition": {
            "fields": [
                {
                    "type": "vector",
                    "path": "embedding",
                    "numDimensions": config.EMBEDDING_DIM,
                    "similarity": "cosine",
                },
                {"type": "filter", "path": "source_document"},
            ]
        },
    }
    try:
        chunks_collection().create_search_index(index_def)
        print(f"Requested creation of vector index '{config.VECTOR_INDEX_NAME}' "
              f"-- it can take a minute or two to finish building on Atlas.")
    except Exception as exc:
        print(f"[!] Could not auto-create the vector index ({exc}).")
        print("    Create it manually in Atlas UI (Search > Create Search "
              "Index > JSON Editor) on the "
              f"'{config.CHUNKS_COLLECTION}' collection using:\n")
        import json
        print(json.dumps(index_def, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="Ingest only this source_document label")
    parser.add_argument("--skip-index", action="store_true",
                         help="Skip vector search index creation")
    args = parser.parse_args()

    doc_map = config.DOCUMENT_MAP
    if args.only:
        doc_map = {p: n for p, n in doc_map.items() if n == args.only}
        if not doc_map:
            print(f"No document labeled '{args.only}' in config.DOCUMENT_MAP")
            sys.exit(1)

    total = 0
    for pdf_path, source_document in doc_map.items():
        total += ingest_document(pdf_path, source_document)

    print(f"\nDone. {total} chunk(s) embedded and stored in "
          f"{config.DB_NAME}.{config.CHUNKS_COLLECTION}.")

    if not args.skip_index:
        ensure_vector_index()


if __name__ == "__main__":
    main()
