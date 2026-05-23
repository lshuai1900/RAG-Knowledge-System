from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

try:
    from .embeddings import EmbeddingClient
    from .hybrid_search import HybridSearch
    from .vector_store import LocalVectorStore, _normalize_matrix, _normalize_vector
except ImportError:  # pragma: no cover - direct script fallback
    from embeddings import EmbeddingClient
    from hybrid_search import HybridSearch
    from vector_store import LocalVectorStore, _normalize_matrix, _normalize_vector


class Retriever:
    def __init__(
        self,
        index_dir: str | Path | None = None,
        embedding_client: EmbeddingClient | None = None,
    ):
        self.store = LocalVectorStore(index_dir) if index_dir else LocalVectorStore()
        self.embedding_client = embedding_client or EmbeddingClient()
        self.hybrid_search = HybridSearch(index_dir or self.store.index_dir)

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        retrieval_mode: str = "hybrid",
        fusion: str = "rrf",
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3,
        use_mmr: bool = False,
        lambda_mult: float = 0.5,
    ) -> list[dict[str, Any]]:
        mode = (retrieval_mode or "hybrid").strip().lower()
        if mode not in {"vector", "keyword", "hybrid"}:
            mode = "hybrid"

        dense_results: list[dict[str, Any]] = []
        sparse_results: list[dict[str, Any]] = []
        if mode in {"vector", "hybrid"}:
            query_embedding = await self.embedding_client.embed_query(query)
            if use_mmr:
                dense_results = self._mmr_search(query_embedding, top_k=top_k, lambda_mult=lambda_mult)
            else:
                dense_results = self.store.search_by_vector(query_embedding, top_k=top_k)
            for item in dense_results:
                score = float(item.get("score") or 0.0)
                item["dense_score"] = round(score, 6)
                item["sparse_score"] = 0.0
                item["fusion_score"] = round(score, 6)
                item["score"] = round(score, 6)

        if mode in {"keyword", "hybrid"}:
            sparse_results = self.hybrid_search.keyword_search(query, top_k=top_k)
            for item in sparse_results:
                score = float(item.get("sparse_score") or 0.0)
                item["dense_score"] = 0.0
                item["sparse_score"] = round(score, 6)
                item["fusion_score"] = round(score, 6)
                item["score"] = round(score, 6)

        if mode == "vector":
            return dense_results
        if mode == "keyword":
            return sparse_results

        return self._fuse_results(
            dense_results,
            sparse_results,
            top_k=top_k,
            fusion=fusion,
            dense_weight=dense_weight,
            sparse_weight=sparse_weight,
        )

    def _mmr_search(self, query_embedding: list[float], top_k: int, lambda_mult: float) -> list[dict[str, Any]]:
        embeddings, records = self.store.load()
        if embeddings.size == 0 or not records:
            return []

        normalized_embeddings = _normalize_matrix(embeddings)
        query = _normalize_vector(np.array(query_embedding, dtype=np.float32))
        query_scores = normalized_embeddings @ query

        selected: list[int] = []
        candidates = set(range(len(records)))
        while candidates and len(selected) < top_k:
            if not selected:
                best = max(candidates, key=lambda idx: query_scores[idx])
            else:
                selected_matrix = normalized_embeddings[selected]
                best = max(
                    candidates,
                    key=lambda idx: (
                        lambda_mult * query_scores[idx]
                        - (1.0 - lambda_mult) * float(np.max(selected_matrix @ normalized_embeddings[idx]))
                    ),
                )
            selected.append(int(best))
            candidates.remove(best)

        results: list[dict[str, Any]] = []
        for idx in selected:
            record = records[idx]
            results.append({
                "chunk_id": record.get("chunk_id"),
                "chunk_text": record.get("chunk_text", ""),
                "score": round(float(query_scores[idx]), 6),
                "metadata": record.get("metadata", {}),
                "embedding_index": idx,
                "retrieval_strategy": "mmr",
            })
        return results

    @staticmethod
    def _normalize_scores(items: list[dict[str, Any]], key: str) -> dict[str, float]:
        scores: list[float] = []
        for item in items:
            score = float(item.get(key) or 0.0)
            scores.append(score)
        if not scores:
            return {}
        min_score = min(scores)
        max_score = max(scores)
        normalized: dict[str, float] = {}
        for item in items:
            raw = float(item.get(key) or 0.0)
            if max_score == min_score:
                normalized[item.get("chunk_id")] = 1.0 if max_score > 0 else 0.0
            else:
                normalized[item.get("chunk_id")] = (raw - min_score) / (max_score - min_score)
        return normalized

    def _fuse_results(
        self,
        dense_results: list[dict[str, Any]],
        sparse_results: list[dict[str, Any]],
        top_k: int,
        fusion: str,
        dense_weight: float,
        sparse_weight: float,
    ) -> list[dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}
        for item in dense_results:
            key = item.get("chunk_id")
            if key is None:
                continue
            merged[key] = dict(item)
        for item in sparse_results:
            key = item.get("chunk_id")
            if key is None:
                continue
            if key in merged:
                merged[key]["sparse_score"] = float(item.get("sparse_score") or 0.0)
            else:
                merged[key] = dict(item)

        if not merged:
            return []

        fusion_mode = (fusion or "rrf").strip().lower()
        if fusion_mode == "rrf":
            rrf_k = 60
            dense_rank = {item.get("chunk_id"): rank for rank, item in enumerate(dense_results, start=1)}
            sparse_rank = {item.get("chunk_id"): rank for rank, item in enumerate(sparse_results, start=1)}
            for key, item in merged.items():
                score = 0.0
                if key in dense_rank:
                    score += 1.0 / (rrf_k + dense_rank[key])
                if key in sparse_rank:
                    score += 1.0 / (rrf_k + sparse_rank[key])
                item["fusion_score"] = round(score, 6)
                item["score"] = item["fusion_score"]
        else:
            dense_norm = self._normalize_scores(dense_results, "dense_score")
            sparse_norm = self._normalize_scores(sparse_results, "sparse_score")
            for key, item in merged.items():
                dn = dense_norm.get(key, 0.0)
                sn = sparse_norm.get(key, 0.0)
                fusion_score = dense_weight * dn + sparse_weight * sn
                item["fusion_score"] = round(fusion_score, 6)
                item["score"] = item["fusion_score"]

        ranked = sorted(merged.values(), key=lambda x: float(x.get("fusion_score") or 0.0), reverse=True)
        return ranked[:top_k]
