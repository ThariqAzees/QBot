"""
Creates the Atlas Vector Search index on chat_history.question_embedding,
used for the "related questions" feature. Safe to run once, up front --
Atlas Search indexes can be created on an empty collection.

    python setup_history_index.py
"""
import json

import config
from utils.mongo_client import history_collection

index_def = {
    "name": config.HISTORY_VECTOR_INDEX_NAME,
    "type": "vectorSearch",
    "definition": {
        "fields": [
            {
                "type": "vector",
                "path": "question_embedding",
                "numDimensions": config.EMBEDDING_DIM,
                "similarity": "cosine",
            },
            {"type": "filter", "path": "session_id"},
        ]
    },
}

if __name__ == "__main__":
    try:
        history_collection().create_search_index(index_def)
        print(f"Requested creation of '{config.HISTORY_VECTOR_INDEX_NAME}'. "
              f"It can take a minute or two to finish building on Atlas.")
    except Exception as exc:
        print(f"[!] Could not auto-create the index ({exc}).")
        print("    Create it manually in Atlas UI (Search > Create Search "
              f"Index > JSON Editor) on the '{config.HISTORY_COLLECTION}' "
              "collection using:\n")
        print(json.dumps(index_def, indent=2))
