"""RAG status endpoint — calls rag.service (Yuxi-style)."""

import os
import logging

from fastapi import APIRouter

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/status")
async def get_rag_status():
    """Return real-time RAG engine status.

    Prefer rag.service; fall back to env-only status on bootstrap failure.
    """
    try:
        from rag.service import rag_service
        return rag_service.get_status()
    except Exception as exc:
        logger.warning("rag.service unavailable: %s; using fallback status", exc)
        return _fallback_status()


def _fallback_status() -> dict:
    return {
        "rag_engine": os.getenv("RAG_ENGINE", "rag_lab"),
        "embedding_provider": os.getenv("EMBEDDING_PROVIDER", "openai"),
        "embedding_model": os.getenv("EMBED_MODEL", "—"),
        "embedding_dim": int(os.getenv("EMBEDDING_DIM", "1024")),
        "index_embedding_dim": 0,
        "chunk_strategy": os.getenv("CHUNK_STRATEGY") or settings.CHUNK_STRATEGY,
        "chunk_size": int(os.getenv("CHUNK_SIZE", settings.CHUNK_SIZE)),
        "chunk_overlap": int(os.getenv("CHUNK_OVERLAP", settings.CHUNK_OVERLAP)),
        "chunk_min_size": int(os.getenv("CHUNK_MIN_SIZE", "100")),
        "retrieval_mode": os.getenv("RAG_RETRIEVAL_MODE", "hybrid"),
        "hybrid_fusion": os.getenv("RAG_HYBRID_FUSION", "rrf"),
        "use_rerank": os.getenv("RAG_USE_RERANK", "false").lower() in {"1", "true"},
        "rerank_model": os.getenv("RERANKER_MODEL", ""),
        "rerank_top_n": int(os.getenv("RAG_RERANK_TOP_N", "5")),
        "documents_count": 0, "chunks_count": 0,
        "index_ready": False, "last_index_time": None,
        "last_eval_time": None, "last_eval_score": None,
        "health": "fallback",
        "warnings": ["Using fallback status — rag.service unavailable"],
        "RAG_ENGINE": os.getenv("RAG_ENGINE", "rag_lab"),
        "CHUNK_STRATEGY": os.getenv("CHUNK_STRATEGY") or settings.CHUNK_STRATEGY,
        "RAG_RETRIEVAL_MODE": os.getenv("RAG_RETRIEVAL_MODE", "hybrid"),
        "RAG_HYBRID_FUSION": os.getenv("RAG_HYBRID_FUSION", "rrf"),
        "RAG_USE_RERANK": os.getenv("RAG_USE_RERANK", "false").lower() in {"1", "true"},
        "RAG_RERANK_TOP_N": int(os.getenv("RAG_RERANK_TOP_N", "5")),
    }
