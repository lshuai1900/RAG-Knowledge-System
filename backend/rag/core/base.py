"""Abstract base classes for RAG components — Yuxi-style.

Every pluggable component (parser, chunker, embedding provider, retriever,
vector store, document store) inherits from one of these.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .schemas import (
    ParseResult,
    ChunkRecord,
    EmbeddingResult,
    RetrievalResult,
)


class BaseParser(ABC):
    """Parse a single document file into text + metadata."""

    name: str = "base"

    @abstractmethod
    def parse(self, path: Path) -> ParseResult:
        ...

    @classmethod
    @abstractmethod
    def accepts(cls) -> set[str]:
        ...

    def supports(self, extension: str) -> bool:
        return extension.strip().lower() in self.accepts()


class BaseChunker(ABC):
    """Split parsed text into chunks according to a strategy."""

    name: str = "base"

    @abstractmethod
    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[ChunkRecord]:
        ...


class BaseEmbeddingProvider(ABC):
    """Generate embeddings for text chunks."""

    name: str = "base"
    is_configured: bool = True

    @abstractmethod
    async def embed(self, chunks: list[ChunkRecord]) -> EmbeddingResult:
        ...

    async def _embed_text(self, text: str) -> list[float]:
        """Embed a single text query — used for retrieval."""
        from .schemas import ChunkRecord
        result = await self.embed([ChunkRecord(
            chunk_id="__query__", doc_id="__query__", kb_id="__query__",
            text=text, chunk_index=0,
        )])
        return result.embeddings[0] if result.embeddings else [0.0] * self.dimension

    @property
    @abstractmethod
    def dimension(self) -> int:
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...


class BaseRetriever(ABC):
    """Search chunks given a query."""

    @abstractmethod
    async def retrieve(
        self, query: str, kb_id: str, top_k: int = 5, **kwargs: Any,
    ) -> list[RetrievalResult]:
        ...


class BaseVectorStore(ABC):
    """Persist and search vector embeddings."""

    @abstractmethod
    async def save(self, embedding_result: EmbeddingResult, kb_id: str) -> None:
        ...

    @abstractmethod
    async def search(
        self, query_vector: list[float], kb_id: str, top_k: int = 5,
    ) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def exists(self, kb_id: str) -> bool:
        ...

    @abstractmethod
    async def delete(self, kb_id: str) -> None:
        ...


class BaseDocumentStore(ABC):
    """Store and query document / chunk metadata."""

    @abstractmethod
    async def save_document(self, record) -> None:
        ...

    @abstractmethod
    async def get_document(self, doc_id: str) -> dict | None:
        ...

    @abstractmethod
    async def list_documents(self, kb_id: str) -> list[dict]:
        ...

    @abstractmethod
    async def save_chunks(self, chunks: list[ChunkRecord]) -> None:
        ...

    @abstractmethod
    async def get_chunks(self, kb_id: str) -> list[ChunkRecord]:
        ...
