"""Unified exception hierarchy for the RAG module."""


class RagError(Exception):
    """Base for all RAG module errors."""


class ParserNotFoundError(RagError):
    """No parser registered for the given file type."""


class ChunkStrategyError(RagError):
    """Unknown or unsupported chunk strategy."""


class EmbeddingError(RagError):
    """Embedding provider failed to generate vectors."""


class IndexNotReadyError(RagError):
    """Vector index is not built or is stale."""


class KnowledgeBaseNotFoundError(RagError):
    """Requested knowledge base does not exist."""


class DocumentNotFoundError(RagError):
    """Requested document does not exist."""


class DimensionMismatchError(RagError):
    """Stored index dimension does not match current embedding dimension."""
