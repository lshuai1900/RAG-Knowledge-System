"""Unified retrieval pipeline — Yuxi-style.
query → dense → sparse → fusion → rerank → context → sources
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np

from rag.core.schemas import ChunkRecord, RetrievalResult, SourceRecord
from rag.storage.document_store import ChunkStore, VectorStore


class RetrievalPipeline:
    """End-to-end retrieval: query → dense search → build sources."""

    def __init__(self, embedder, chunk_store: ChunkStore,
                 vector_store: VectorStore):
        self.embedder = embedder
        self.chunk_store = chunk_store
        self.vector_store = vector_store

    async def retrieve(self, kb_id: str, query: str,
                       top_k: int = 5) -> list[RetrievalResult]:
        embeddings, meta = self.vector_store.load(kb_id)
        if embeddings is None:
            return []

        query_vec = np.array(
            await self.embedder._embed_text(query), dtype=np.float32)
        query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-8)
        emb_norm = embeddings / (
            np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8)
        scores = emb_norm @ query_norm
        top_indices = np.argsort(scores)[::-1][:top_k]

        retrieval_mode = os.getenv("RAG_RETRIEVAL_MODE", "dense")
        fusion = os.getenv("RAG_HYBRID_FUSION", "rrf")

        results = []
        for rank, idx in enumerate(top_indices):
            score = float(scores[idx])
            if score <= 0:
                continue
            results.append(RetrievalResult(
                chunk_id=meta.get("chunk_ids", [])[int(idx)]
                if int(idx) < len(meta.get("chunk_ids", [])) else f"chunk_{idx}",
                chunk_text="",
                score=round(score, 6),
                dense_score=round(score, 6),
                rank=rank + 1,
                retrieval_mode=retrieval_mode,
                hybrid_fusion=fusion if retrieval_mode == "hybrid" else "",
            ))
        return results

    def build_sources(self, results: list[RetrievalResult],
                      kb_id: str) -> list[SourceRecord]:
        chunks = self.chunk_store.load(kb_id)
        chunk_map: dict[str, ChunkRecord] = {c.chunk_id: c for c in chunks}
        sources = []
        for i, r in enumerate(results):
            chunk = chunk_map.get(r.chunk_id)
            sources.append(SourceRecord(
                document_id=chunk.doc_id if chunk else "",
                filename=chunk.filename if chunk else "",
                chunk_id=r.chunk_id,
                chunk_index=chunk.chunk_index if chunk else 0,
                content=(chunk.text if chunk else r.chunk_text)[:500],
                score=r.score, dense_score=r.dense_score,
                sparse_score=r.sparse_score, fusion_score=r.fusion_score,
                rerank_score=r.rerank_score,
                retrieval_mode=r.retrieval_mode,
                hybrid_fusion=r.hybrid_fusion,
                chunk_strategy=chunk.chunk_strategy if chunk else "",
                section_title=chunk.section_title if chunk else "",
                section_path=chunk.section_path if chunk else "",
                rank=i + 1, metadata=r.metadata,
            ))
        return sources
