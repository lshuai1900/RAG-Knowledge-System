"""Bootstrap — register all components into the Yuxi-style factory.

Called once at application startup.  Registers parsers, chunkers and
embedding providers so the KnowledgeBaseManager can resolve them at runtime.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def bootstrap() -> None:
    """Wire all RAG components into the global factory."""
    _bootstrap_parsers()
    _bootstrap_chunkers()
    _bootstrap_embeddings()
    logger.info("[RAG Bootstrap] All components registered")


def _bootstrap_parsers() -> None:
    from rag.core.factory import rag_factory

    # Register parsers from yuxi_rag
    _rag_lab_dir = Path(__file__).resolve().parents[1] / "rag_lab"
    if str(_rag_lab_dir) not in sys.path:
        sys.path.insert(0, str(_rag_lab_dir))

    try:
        from yuxi_rag.parsers import TextParser, PdfParser, DocxParser
        rag_factory.register_parser(TextParser())
        rag_factory.register_parser(PdfParser())
        rag_factory.register_parser(DocxParser())
        logger.info("[RAG Bootstrap] Parsers registered: txt, md, pdf, docx")
    except ImportError:
        # Register built-in parsers directly
        from rag.parsers_registry import TextParser, PdfParser, DocxParser
        rag_factory.register_parser(TextParser())
        rag_factory.register_parser(PdfParser())
        rag_factory.register_parser(DocxParser())
        logger.info("[RAG Bootstrap] Parsers registered (built-in)")


def _bootstrap_chunkers() -> None:
    from rag.core.factory import rag_factory
    from rag.chunking import (
        RecursiveChunker, MarkdownHeaderChunker,
        SentenceWindowChunker, ParagraphChunker,
    )

    rag_factory.register_chunker("recursive", RecursiveChunker())
    rag_factory.register_chunker("markdown_header", MarkdownHeaderChunker())
    rag_factory.register_chunker("sentence_window", SentenceWindowChunker())
    rag_factory.register_chunker("paragraph", ParagraphChunker())
    logger.info("[RAG Bootstrap] Chunkers registered: recursive, markdown_header, sentence_window, paragraph")


def _bootstrap_embeddings() -> None:
    from rag.core.factory import rag_factory
    from rag.embeddings.factory import register_providers, get_provider

    register_providers()
    provider = get_provider()
    rag_factory.register_embedding_provider(provider)
    logger.info("[RAG Bootstrap] Embedding provider: %s (dim=%d)", provider.name, provider.dimension)
