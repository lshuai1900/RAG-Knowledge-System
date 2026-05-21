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

        # Attach similarity_score derived from COSINE distance.
        # Milvus COSINE distance = 1 - cosine_similarity, so smaller = more relevant.
        for h in hits:
            raw = h.get("score", 1.0)
            h["raw_score"] = raw
            h["similarity_score"] = round(1.0 - raw, 4)

        # Return all hits; threshold filtering is done in RAGService._check_confidence
        # so we can report precise rejection reasons.
        return hits
