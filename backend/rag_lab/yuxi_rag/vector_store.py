from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

try:
    from .chunker import Chunk
except ImportError:  # pragma: no cover - direct script fallback
    from chunker import Chunk

RAG_LAB_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INDEX_DIR = RAG_LAB_DIR / "data" / "index"


def _normalize_matrix(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def _normalize_vector(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    if norm == 0:
        return vector
    return vector / norm


class LocalVectorStore:
    def __init__(self, index_dir: str | Path = DEFAULT_INDEX_DIR):
        self.index_dir = Path(index_dir)
        self.embeddings_path = self.index_dir / "embeddings.npy"
        self.metadata_path = self.index_dir / "metadata.json"
        self._embeddings: np.ndarray | None = None
        self._records: list[dict[str, Any]] | None = None

    def save(self, embeddings: list[list[float]], chunks: list[Chunk]) -> None:
        if len(embeddings) != len(chunks):
            raise ValueError("embeddings and chunks length mismatch")
        self.index_dir.mkdir(parents=True, exist_ok=True)
        matrix = np.array(embeddings, dtype=np.float32)
        np.save(self.embeddings_path, matrix)
        records = [chunk.to_dict() for chunk in chunks]
        with self.metadata_path.open("w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        self._embeddings = matrix
        self._records = records

    def exists(self) -> bool:
        return self.embeddings_path.exists() and self.metadata_path.exists()

    def load(self) -> tuple[np.ndarray, list[dict[str, Any]]]:
        if self._embeddings is None:
            if not self.embeddings_path.exists():
                raise FileNotFoundError(f"Missing embeddings index: {self.embeddings_path}")
            self._embeddings = np.load(self.embeddings_path)
        if self._records is None:
            if not self.metadata_path.exists():
                raise FileNotFoundError(f"Missing metadata index: {self.metadata_path}")
            with self.metadata_path.open("r", encoding="utf-8") as f:
                self._records = json.load(f)
        return self._embeddings, self._records

    def search_by_vector(self, query_embedding: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        embeddings, records = self.load()
        if embeddings.size == 0 or not records:
            return []
        normalized_embeddings = _normalize_matrix(embeddings)
        query = _normalize_vector(np.array(query_embedding, dtype=np.float32))
        scores = normalized_embeddings @ query
        top_indices = np.argsort(scores)[::-1][:top_k]
        results: list[dict[str, Any]] = []
        for idx in top_indices:
            record = records[int(idx)]
            results.append({
                "chunk_id": record.get("chunk_id"),
                "chunk_text": record.get("chunk_text", ""),
                "score": round(float(scores[int(idx)]), 6),
                "metadata": record.get("metadata", {}),
                "embedding_index": int(idx),
            })
        return results

    def all_embeddings(self) -> tuple[np.ndarray, list[dict[str, Any]]]:
        return self.load()
