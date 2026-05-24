"""Yuxi-style component factory.

Resolves the correct parser / chunker / embedding provider at runtime
based on file type, configuration, and registered components.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from .base import BaseParser, BaseChunker, BaseEmbeddingProvider
from .exceptions import ParserNotFoundError, ChunkStrategyError

logger = logging.getLogger(__name__)

# ── Supported strategies ───────────────────────────────────────────

SUPPORTED_CHUNK_STRATEGIES = frozenset({
    "recursive", "markdown_header", "sentence_window",
    "paragraph", "auto", "semantic",
})


def resolve_strategy(requested: str | None = None, file_type: str = "") -> str:
    """Resolve chunk strategy with auto-detection.

    ``auto`` applies these rules:
    - .md → markdown_header
    - .txt → sentence_window
    - .pdf / .docx → recursive
    - unknown → recursive
    """
    strategy = (requested or os.getenv("CHUNK_STRATEGY") or "auto").strip().lower()

    if strategy == "semantic":
        strategy = "paragraph"

    if strategy == "auto":
        ext = file_type.lower().lstrip(".")
        if ext in {"md", "markdown"}:
            resolved = "markdown_header"
        elif ext in {"txt", "text"}:
            resolved = "sentence_window"
        else:
            resolved = "recursive"
        logger.info("[RagFactory] auto strategy → %s (file_type=%s)", resolved, file_type)
        return resolved

    if strategy not in SUPPORTED_CHUNK_STRATEGIES:
        logger.warning("[RagFactory] Unknown strategy=%s; falling back to recursive", strategy)
        return "recursive"

    return strategy


class ParserRegistry:
    """Registers and resolves document parsers by file extension."""

    def __init__(self):
        self._parsers: dict[str, BaseParser] = {}

    def register(self, parser: BaseParser) -> None:
        for ext in parser.accepts():
            self._parsers[ext] = parser
        logger.debug("[ParserRegistry] registered %s for %s", parser.name, parser.accepts())

    def get(self, extension: str) -> BaseParser:
        ext = extension.strip().lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        parser = self._parsers.get(ext)
        if parser is None:
            raise ParserNotFoundError(f"No parser for extension: {ext}")
        return parser

    def parse(self, path: Path) -> Any:
        ext = path.suffix.lower()
        return self.get(ext).parse(path)

    @property
    def supported_extensions(self) -> set[str]:
        return set(self._parsers.keys())


class RagComponentFactory:
    """Top-level factory that wires parsers, chunkers and embedding providers."""

    def __init__(self):
        self.parser_registry = ParserRegistry()
        self._chunkers: dict[str, BaseChunker] = {}
        self._embedding_providers: dict[str, BaseEmbeddingProvider] = {}

    # ── Parser ─────────────────────────────────────────────────────

    def register_parser(self, parser: BaseParser) -> None:
        self.parser_registry.register(parser)

    def get_parser(self, extension: str) -> BaseParser:
        return self.parser_registry.get(extension)

    # ── Chunker ────────────────────────────────────────────────────

    def register_chunker(self, strategy: str, chunker: BaseChunker) -> None:
        self._chunkers[strategy.strip().lower()] = chunker

    def get_chunker(self, strategy: str, file_type: str = "") -> BaseChunker:
        resolved = resolve_strategy(strategy, file_type)
        chunker = self._chunkers.get(resolved)
        if chunker is None:
            raise ChunkStrategyError(f"No chunker registered for: {resolved}")
        return chunker

    # ── Embedding ──────────────────────────────────────────────────

    def register_embedding_provider(self, provider: BaseEmbeddingProvider) -> None:
        self._embedding_providers[provider.name] = provider

    def get_embedding_provider(self, name: str | None = None) -> BaseEmbeddingProvider:
        provider_name = name or os.getenv("EMBEDDING_PROVIDER", "openai")
        provider = self._embedding_providers.get(provider_name)
        if provider is None:
            fallback = self._embedding_providers.get("openai")
            if fallback is None and self._embedding_providers:
                fallback = next(iter(self._embedding_providers.values()))
            if fallback is None:
                raise EmbeddingError("No embedding provider registered")
            logger.warning(
                "[RagFactory] Provider '%s' not found; using '%s'",
                provider_name, fallback.name,
            )
            return fallback
        return provider


# Module-level singleton
rag_factory = RagComponentFactory()


# Re-import EmbeddingError for local use
from .exceptions import EmbeddingError  # noqa: E402
