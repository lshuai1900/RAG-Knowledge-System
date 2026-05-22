from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

try:
    from .embeddings import EmbeddingClient
    from .vector_store import LocalVectorStore, _normalize_matrix, _normalize_vector
except ImportError:  # pragma: no cover - direct script fallback
    from embeddings import EmbeddingClient
    from vector_store import LocalVectorStore, _normalize_matrix, _normalize_vector


class Retriever:
    def __init__(
        self,
        index_dir: str | Path | None = None,
        embedding_client: EmbeddingClient | None = None,
    ):
        self.store = LocalVectorStore(index_dir) if index_dir else LocalVectorStore()
        self.embedding_client = embedding_client or EmbeddingClient()

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        use_mmr: bool = False,
        lambda_mult: float = 0.5,
    ) -> list[dict[str, Any]]:
        query_embedding = await self.embedding_client.embed_query(query)
        if use_mmr:
            return self._mmr_search(query_embedding, top_k=top_k, lambda_mult=lambda_mult)
        return self.store.search_by_vector(query_embedding, top_k=top_k)

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
