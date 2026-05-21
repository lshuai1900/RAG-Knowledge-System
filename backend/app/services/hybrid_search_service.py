import logging
import asyncio

from app.config import settings
from app.services.retrieval_service import RetrievalService
from app.services.bm25_service import bm25_service

logger = logging.getLogger(__name__)


class HybridSearchService:
    """Orchestrate vector + BM25 hybrid search with merge, dedup, and score fusion.

    When ``ENABLE_HYBRID_SEARCH`` is false, delegates entirely to vector search
    so the system behaves exactly as Phase 3.
    """

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
        """Hybrid search entry point.

        When disabled, this is a transparent pass-through to vector search.
        """
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

        for h in vector_hits:
            key = (h.get("doc_id", ""), h.get("chunk_index", 0))
            h["vector_score"] = h.get("similarity_score", 0.0)
            h["bm25_score"] = None
            h["bm25_score_norm"] = 0.0
            vec_s = h["vector_score"] or 0.0
            h["hybrid_score"] = round(self.alpha * vec_s, 4)
            h["effective_score"] = vec_s
            h["retrieval_source"] = "vector"
            merged[key] = h

        for h in bm25_hits:
            key = (h.get("doc_id", ""), h.get("chunk_index", 0))
            bm25_norm = h.get("bm25_score_norm", 0.0)
            bm25_raw = h.get("bm25_score")

            if key in merged:
                existing = merged[key]
                existing["bm25_score"] = bm25_raw
                existing["bm25_score_norm"] = bm25_norm
                existing["retrieval_source"] = "hybrid"
                vec_s = existing.get("vector_score") or 0.0
                existing["hybrid_score"] = round(
                    self.alpha * vec_s + (1 - self.alpha) * bm25_norm, 4,
                )
                existing["effective_score"] = existing["hybrid_score"]
            else:
                # BM25-only — no vector signal; effective_score uses the
                # full normalized BM25 score so it can be thresholded fairly.
                h["vector_score"] = None
                h["hybrid_score"] = round((1 - self.alpha) * bm25_norm, 4)
                h["effective_score"] = bm25_norm
                h["retrieval_source"] = "bm25"
                merged[key] = h

        return list(merged.values())
