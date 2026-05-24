import os

from app.db.milvus_client import milvus_client
from app.services.embedding_service import embedding_service
from app.config import settings


class RetrievalService:
    def __init__(self):
        self.top_k = settings.TOP_K
        self.score_threshold = settings.SIMILARITY_SCORE_THRESHOLD

    async def search(self, kb_id: str, query: str, top_k: int | None = None) -> list[dict]:
        k = top_k if top_k is not None else self.top_k
        query_vector = await embedding_service.embed_query(query)
        hits = await milvus_client.search(kb_id, query_vector, k)

        chunk_strategy = os.getenv("CHUNK_STRATEGY") or settings.CHUNK_STRATEGY
        for h in hits:
            raw = h.get("score", 1.0)
            h["raw_score"] = raw
            h["similarity_score"] = round(1.0 - raw, 4)
            h["dense_score"] = round(1.0 - raw, 4)
            h["retrieval_mode"] = "vector"
            h["chunk_strategy"] = h.get("chunk_strategy") or chunk_strategy

        return hits
