"""MongoDB connection helper."""
from pymongo import MongoClient

import config

_client = None


def client() -> MongoClient:
    global _client
    if _client is None:
        if not config.MONGODB_URI:
            raise RuntimeError(
                "MONGODB_URI is not set. Copy .env.example to .env and "
                "fill it in with your Atlas connection string."
            )
        _client = MongoClient(config.MONGODB_URI)
    return _client


def db():
    return client()[config.DB_NAME]


def chunks_collection():
    return db()[config.CHUNKS_COLLECTION]


def history_collection():
    return db()[config.HISTORY_COLLECTION]
