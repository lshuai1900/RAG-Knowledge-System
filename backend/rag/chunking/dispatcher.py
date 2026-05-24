"""ChunkingDispatcher — routes to correct chunker based on strategy + file type."""

from __future__ import annotations

import logging
from typing import Any

from rag.core.base import BaseChunker
from rag.core.schemas import ChunkRecord
from rag.core.factory import resolve_strategy

from .recursive import RecursiveChunker
from .markdown_header import MarkdownHeaderChunker
from .sentence_window import SentenceWindowChunker
from .paragraph_chunker import ParagraphChunker

logger = logging.getLogger(__name__)


class ChunkingDispatcher(BaseChunker):
    """Single entry point that delegates to the appropriate chunker."""

    name = "dispatcher"

    def __init__(self):
        self._chunkers: dict[str, BaseChunker] = {
            "recursive": RecursiveChunker(),
            "markdown_header": MarkdownHeaderChunker(),
            "sentence_window": SentenceWindowChunker(),
            "paragraph": ParagraphChunker(),
        }

    def register(self, strategy: str, chunker: BaseChunker) -> None:
        self._chunkers[strategy.strip().lower()] = chunker

    def get_chunker(self, strategy: str | None = None,
                    file_type: str = "") -> BaseChunker:
        resolved = resolve_strategy(strategy, file_type)
        chunker = self._chunkers.get(resolved)
        if chunker is None:
            logger.warning("No chunker for strategy=%s; using recursive", resolved)
            chunker = self._chunkers["recursive"]
        return chunker

    def chunk(self, text: str, metadata: dict[str, Any] | None = None,
              strategy: str | None = None, file_type: str = "") -> list[ChunkRecord]:
        chunker = self.get_chunker(strategy, file_type)
        logger.info("[ChunkingDispatcher] strategy=%s chunker=%s", strategy or "auto", chunker.name)
        return chunker.chunk(text, metadata)


_dispatcher: ChunkingDispatcher | None = None


def get_dispatcher() -> ChunkingDispatcher:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = ChunkingDispatcher()
    return _dispatcher
