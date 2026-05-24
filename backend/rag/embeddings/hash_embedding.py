"""Hash-based embedding provider — works without any API key.

Uses SHA-256 hashing to produce deterministic pseudo-embeddings.
Suitable for demo / smoke-test / offline development.
Similarity scores are NOT semantically meaningful; this is a
stand-in that lets the full RAG pipeline run without credentials.
"""

from __future__ import annotations

import hashlib
import struct

from rag.core.base import BaseEmbeddingProvider
from rag.core.schemas import ChunkRecord, EmbeddingResult


class HashEmbeddingProvider(BaseEmbeddingProvider):
    name = "hash"
    _DIM = 256

    @property
    def dimension(self) -> int:
        return self._DIM

    @property
    def model_name(self) -> str:
        return "hash-sha256-256d"

    async def embed(self, chunks: list[ChunkRecord]) -> EmbeddingResult:
        embeddings: list[list[float]] = []
        for chunk in chunks:
            vec = self._hash_embed(chunk.text)
            embeddings.append(vec)
        return EmbeddingResult(
            chunks=chunks, embeddings=embeddings,
            model=self.model_name, dimension=self._DIM, provider=self.name,
        )

    async def _embed_text(self, text: str) -> list[float]:
        return self._hash_embed(text)

    @staticmethod
    def _hash_embed(text: str) -> list[float]:
        h = hashlib.sha256(text.encode("utf-8")).digest()
        floats = []
        for i in range(0, 32, 4):
            val = struct.unpack(">I", h[i:i + 4])[0]
            floats.append((val / 0xFFFFFFFF) * 2.0 - 1.0)
        # Pad to _DIM
        while len(floats) < HashEmbeddingProvider._DIM:
            floats.append(floats[len(floats) % 8] * 0.5)
        return floats[:HashEmbeddingProvider._DIM]
