from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

try:
    from .vector_store import LocalVectorStore, DEFAULT_INDEX_DIR
except ImportError:  # pragma: no cover - direct script fallback
    from vector_store import LocalVectorStore, DEFAULT_INDEX_DIR


def _tokenize(text: str) -> list[str]:
    cleaned = (text or "").strip()
    if not cleaned:
        return []
    try:
        import jieba

        tokens = [t.strip() for t in jieba.lcut(cleaned) if t.strip()]
        if tokens:
            return tokens
    except Exception:
        pass
    return [t for t in cleaned.lower().split() if t.strip()]


class HybridSearch:
    def __init__(self, index_dir: str | Path = DEFAULT_INDEX_DIR):
        self.store = LocalVectorStore(index_dir)
        self._records: list[dict[str, Any]] | None = None
        self._bm25 = None

    def _load_records(self) -> list[dict[str, Any]]:
        if self._records is None:
            _, records = self.store.load()
            self._records = records
        return self._records

    def _ensure_bm25(self):
        if self._bm25 is not None:
            return
        try:
            from rank_bm25 import BM25Okapi
        except Exception as exc:  # pragma: no cover - dependency issue
            raise RuntimeError("rank-bm25 is required for keyword search") from exc
        records = self._load_records()
        corpus = [_tokenize(record.get("chunk_text", "")) for record in records]
        self._bm25 = BM25Okapi(corpus)

    def keyword_search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        self._ensure_bm25()
        records = self._load_records()
        if not records:
            return []
        tokens = _tokenize(query)
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        top_indices = np.argsort(scores)[::-1][:top_k]
        results: list[dict[str, Any]] = []
        for idx in top_indices:
            record = records[int(idx)]
            score = float(scores[int(idx)])
            results.append({
                "chunk_id": record.get("chunk_id"),
                "chunk_text": record.get("chunk_text", ""),
                "sparse_score": round(score, 6),
                "metadata": record.get("metadata", {}),
                "embedding_index": int(idx),
            })
        return results
