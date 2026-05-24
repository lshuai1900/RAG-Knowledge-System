import logging
import os
import asyncio

from app.config import settings
from app.services.retrieval_service import RetrievalService
from app.services.bm25_service import bm25_service

logger = logging.getLogger(__name__)


class HybridSearchService:
    """Orchestrate vector + BM25 hybrid search with merge, dedup, and score fusion."""

    def __init__(self):
        self.enabled = settings.ENABLE_HYBRID_SEARCH
        self.vector = RetrievalService()
        self.vector_top_k = settings.VECTOR_TOP_K
        self.bm25_top_k = settings.BM25_TOP_K
        self.hybrid_top_k = settings.HYBRID_TOP_K
        self.alpha = settings.HYBRID_ALPHA

    async def search(
        self, kb_id: str, query: str, top_k: int | None = None,
    ) -> list[dict]:
        if not self.enabled:
            return await self.vector.search(kb_id, query, top_k)

        vk = top_k if top_k is not None else self.vector_top_k

        vector_results, bm25_results = await asyncio.gather(
            self.vector.search(kb_id, query, vk),
            bm25_service.search(kb_id, query, self.bm25_top_k),
        )

        if not vector_results and not bm25_results:
            return []

        merged = self._merge_and_fuse(vector_results, bm25_results)
        merged.sort(key=lambda h: h.get("effective_score", 0.0), reverse=True)
        return merged[: self.hybrid_top_k]

    # ── Merge & score fusion ─────────────────────────────────────────

    def _merge_and_fuse(
        self,
        vector_hits: list[dict],
        bm25_hits: list[dict],
    ) -> list[dict]:
        """Merge two hit lists, deduplicate by (doc_id, chunk_index), and
        compute fused scores.
        """
        merged: dict[tuple, dict] = {}
        chunk_strategy = os.getenv("CHUNK_STRATEGY") or settings.CHUNK_STRATEGY

        for h in vector_hits:
            key = (h.get("doc_id", ""), h.get("chunk_index", 0))
            h["vector_score"] = h.get("similarity_score", 0.0)
            h["bm25_score"] = None
            h["bm25_score_norm"] = 0.0
            vec_s = h["vector_score"] or 0.0
            h["hybrid_score"] = round(self.alpha * vec_s, 4)
            h["effective_score"] = vec_s
            h["retrieval_source"] = "vector"
            h["dense_score"] = h.get("vector_score") or h.get("similarity_score", 0.0)
            h["retrieval_mode"] = "hybrid"
            h["chunk_strategy"] = h.get("chunk_strategy") or chunk_strategy
            merged[key] = h

        for h in bm25_hits:
            key = (h.get("doc_id", ""), h.get("chunk_index", 0))
            bm25_norm = h.get("bm25_score_norm", 0.0)
            bm25_raw = h.get("bm25_score")

            h["sparse_score"] = bm25_norm
            if key in merged:
                existing = merged[key]
                existing["bm25_score"] = bm25_raw
                existing["bm25_score_norm"] = bm25_norm
                existing["sparse_score"] = bm25_norm
                existing["retrieval_source"] = "hybrid"
                vec_s = existing.get("vector_score") or 0.0
                existing["hybrid_score"] = round(
                    self.alpha * vec_s + (1 - self.alpha) * bm25_norm, 4,
                )
                existing["effective_score"] = existing["hybrid_score"]
            else:
                # BM25-only
                h["vector_score"] = None
                h["dense_score"] = 0.0
                h["sparse_score"] = bm25_norm
                h["hybrid_score"] = round((1 - self.alpha) * bm25_norm, 4)
                h["effective_score"] = bm25_norm
                h["retrieval_source"] = "bm25"
                h["retrieval_mode"] = "hybrid"
                h["chunk_strategy"] = h.get("chunk_strategy") or chunk_strategy
                merged[key] = h

        return list(merged.values())
