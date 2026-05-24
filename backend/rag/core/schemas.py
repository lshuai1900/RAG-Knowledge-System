"""Yuxi-style data schemas for RAG Knowledge System.

All records follow the pattern established in Yuxi's knowledge base model:
consistent field naming, optional metadata dicts, and clear serialisation boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ── Knowledge Base ────────────────────────────────────────────────────

@dataclass(slots=True)
class KnowledgeBaseRecord:
    kb_id: str
    name: str
    description: str = ""
    document_count: int = 0
    chunk_count: int = 0
    embedding_dim: int = 0
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Document ───────────────────────────────────────────────────────────

@dataclass(slots=True)
class DocumentRecord:
    doc_id: str
    kb_id: str
    filename: str
    file_type: str
    file_size: int = 0
    file_path: str = ""
    status: str = "pending"
    chunk_count: int = 0
    chunk_strategy: str = ""
    error_message: str = ""
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_api_dict(self) -> dict:
        return {
            "id": self.doc_id,
            "kb_id": self.kb_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "file_path": self.file_path,
            "status": self.status,
            "chunk_count": self.chunk_count,
            "chunk_strategy": self.chunk_strategy,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ── Parse Result ───────────────────────────────────────────────────────

@dataclass(slots=True)
class ParseResult:
    text: str
    filename: str = ""
    file_type: str = ""
    parser_name: str = ""
    char_count: int = 0
    page_count: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "filename": self.filename,
            "file_type": self.file_type,
            "parser_name": self.parser_name,
            "char_count": self.char_count,
            "page_count": self.page_count,
            "metadata": self.metadata,
        }


# ── Chunk ──────────────────────────────────────────────────────────────

@dataclass(slots=True)
class ChunkRecord:
    chunk_id: str
    doc_id: str
    kb_id: str
    text: str
    chunk_index: int = 0
    start_char: int = 0
    end_char: int = 0
    char_count: int = 0
    token_estimate: int = 0
    chunk_strategy: str = ""
    parser_name: str = ""
    file_type: str = ""
    filename: str = ""
    section_title: str = ""
    section_path: str = ""
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "kb_id": self.kb_id,
            "text": self.text,
            "chunk_index": self.chunk_index,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "char_count": self.char_count,
            "token_estimate": self.token_estimate,
            "chunk_strategy": self.chunk_strategy,
            "parser_name": self.parser_name,
            "file_type": self.file_type,
            "filename": self.filename,
            "section_title": self.section_title,
            "section_path": self.section_path,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


# ── Embedding ──────────────────────────────────────────────────────────

@dataclass(slots=True)
class EmbeddingResult:
    chunks: list[ChunkRecord]
    embeddings: list[list[float]]
    model: str = ""
    dimension: int = 0
    provider: str = ""


# ── Retrieval ──────────────────────────────────────────────────────────

@dataclass(slots=True)
class RetrievalResult:
    chunk_id: str
    chunk_text: str
    score: float = 0.0
    dense_score: float | None = None
    sparse_score: float | None = None
    fusion_score: float | None = None
    rerank_score: float | None = None
    rank: int = 0
    retrieval_mode: str = ""
    hybrid_fusion: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "chunk_text": self.chunk_text,
            "score": self.score,
            "dense_score": self.dense_score,
            "sparse_score": self.sparse_score,
            "fusion_score": self.fusion_score,
            "rerank_score": self.rerank_score,
            "rank": self.rank,
            "retrieval_mode": self.retrieval_mode,
            "hybrid_fusion": self.hybrid_fusion,
            "metadata": self.metadata,
        }


# ── Source (returned to frontend) ──────────────────────────────────────

@dataclass(slots=True)
class SourceRecord:
    document_id: str = ""
    filename: str = ""
    chunk_id: str = ""
    chunk_index: int = 0
    content: str = ""
    score: float = 0.0
    dense_score: float | None = None
    sparse_score: float | None = None
    fusion_score: float | None = None
    rerank_score: float | None = None
    retrieval_mode: str = ""
    hybrid_fusion: str = ""
    chunk_strategy: str = ""
    section_title: str = ""
    section_path: str = ""
    rank: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_api_dict(self) -> dict:
        result: dict[str, Any] = {
            "document_id": self.document_id,
            "document_name": self.filename,
            "filename": self.filename,
            "chunk_id": self.chunk_id,
            "chunk_index": self.chunk_index,
            "content": self.content,
            "content_preview": self.content[:200],
            "score": self.score,
            "dense_score": self.dense_score,
            "sparse_score": self.sparse_score,
            "fusion_score": self.fusion_score,
            "rerank_score": self.rerank_score,
            "retrieval_mode": self.retrieval_mode,
            "hybrid_fusion": self.hybrid_fusion,
            "chunk_strategy": self.chunk_strategy,
            "section_title": self.section_title,
            "section_path": self.section_path,
            "rank": self.rank,
            "metadata": self.metadata,
        }
        # Remove None values
        return {k: v for k, v in result.items() if v is not None}


# ── RAG Status ─────────────────────────────────────────────────────────

@dataclass(slots=True)
class RagStatusInfo:
    rag_engine: str = "rag_lab"
    embedding_provider: str = ""
    embedding_model: str = ""
    embedding_dim: int = 0
    index_embedding_dim: int = 0
    chunk_strategy: str = ""
    chunk_size: int = 0
    chunk_overlap: int = 0
    chunk_min_size: int = 0
    retrieval_mode: str = ""
    hybrid_fusion: str = ""
    use_rerank: bool = False
    rerank_model: str = ""
    rerank_top_n: int = 0
    documents_count: int = 0
    chunks_count: int = 0
    index_ready: bool = False
    last_index_time: str | None = None
    last_query_time: str | None = None
    last_eval_time: str | None = None
    last_eval_score: dict | None = None
    health: str = "unknown"
    warnings: list[str] = field(default_factory=list)

    def to_api_dict(self) -> dict:
        return {
            "rag_engine": self.rag_engine,
            "embedding_provider": self.embedding_provider,
            "embedding_model": self.embedding_model,
            "embedding_dim": self.embedding_dim,
            "index_embedding_dim": self.index_embedding_dim,
            "chunk_strategy": self.chunk_strategy,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "chunk_min_size": self.chunk_min_size,
            "retrieval_mode": self.retrieval_mode,
            "hybrid_fusion": self.hybrid_fusion,
            "use_rerank": self.use_rerank,
            "rerank_model": self.rerank_model,
            "rerank_top_n": self.rerank_top_n,
            "documents_count": self.documents_count,
            "chunks_count": self.chunks_count,
            "index_ready": self.index_ready,
            "last_index_time": self.last_index_time,
            "last_query_time": self.last_query_time,
            "last_eval_time": self.last_eval_time,
            "last_eval_score": self.last_eval_score,
            "health": self.health,
            "warnings": self.warnings,
            # Legacy uppercase fields
            "RAG_ENGINE": self.rag_engine,
            "CHUNK_STRATEGY": self.chunk_strategy,
            "RAG_RETRIEVAL_MODE": self.retrieval_mode,
            "RAG_HYBRID_FUSION": self.hybrid_fusion,
            "RAG_USE_RERANK": self.use_rerank,
            "RAG_RERANK_TOP_N": self.rerank_top_n,
        }


# ── Evaluation ─────────────────────────────────────────────────────────

@dataclass(slots=True)
class EvalReport:
    run_name: str = ""
    generated_at: str = ""
    total_questions: int = 0
    summary: dict[str, float | None] = field(default_factory=dict)
    results: list[dict] = field(default_factory=list)
    ragas_error: str | None = None
