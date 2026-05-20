from app.db.milvus_client import milvus_client
from app.services.embedding_service import embedding_service
from app.config import settings


class RetrievalService:
    def __init__(self):
        self.top_k = settings.TOP_K
        self.score_threshold = settings.SIMILARITY_SCORE_THRESHOLD

    async def search(self, kb_id: str, query: str) -> list[dict]:
        query_vector = await embedding_service.embed_query(query)
        hits = await milvus_client.search(kb_id, query_vector, self.top_k)
        return [h for h in hits if h["score"] >= self.score_threshold]
