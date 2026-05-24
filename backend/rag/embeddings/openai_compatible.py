"""OpenAI-compatible embedding provider.

Uses any OpenAI-compatible embeddings API (OpenAI, DeepSeek, DashScope, etc.).
Configure via environment variables or .env file.
"""

from __future__ import annotations

import os
import logging

from rag.core.base import BaseEmbeddingProvider
from rag.core.schemas import ChunkRecord, EmbeddingResult
from rag.core.exceptions import EmbeddingError

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(BaseEmbeddingProvider):
    name = "openai"

    def __init__(self):
        self._model = os.getenv("EMBED_MODEL") or os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-v4")
        self._api_key = os.getenv("EMBEDDING_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or os.getenv("LLM_API_KEY", "")
        self._base_url = os.getenv("EMBEDDING_API_BASE") or os.getenv("LLM_BASE_URL", "")
        self._dim = int(os.getenv("EMBEDDING_DIM", "1024"))
        self._batch_size = int(os.getenv("EMBEDDING_BATCH_SIZE", "64"))
        self._client = None

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key and self._api_key not in {"your_api_key_here", "", "your_embedding_api_key_here"})

    def _get_client(self):
        if self._client is None:
            if not self.is_configured:
                raise EmbeddingError(
                    "OpenAI-compatible embedding API is not configured. "
                    "Set EMBEDDING_API_KEY in .env, or use EMBEDDING_PROVIDER=hash for demo mode."
                )
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise EmbeddingError("openai package is required for OpenAI-compatible embeddings")
            kwargs = {"api_key": self._api_key}
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    async def embed(self, chunks: list[ChunkRecord]) -> EmbeddingResult:
        client = self._get_client()
        texts = [chunk.text for chunk in chunks]
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), self._batch_size):
            batch = texts[i:i + self._batch_size]
            try:
                resp = await client.embeddings.create(model=self._model, input=batch)
                all_embeddings.extend([d.embedding for d in resp.data])
            except Exception as exc:
                raise EmbeddingError(
                    f"Embedding API failed: {exc}. "
                    f"Check EMBEDDING_API_KEY / EMBEDDING_API_BASE in .env"
                ) from exc

        return EmbeddingResult(
            chunks=chunks, embeddings=all_embeddings,
            model=self._model, dimension=self._dim, provider=self.name,
        )

    async def _embed_text(self, text: str) -> list[float]:
        client = self._get_client()
        resp = await client.embeddings.create(model=self._model, input=[text])
        return resp.data[0].embedding
