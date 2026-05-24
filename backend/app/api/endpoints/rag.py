"""RAG status endpoint — powered by the Yuxi-style KnowledgeBaseManager."""

import os

from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def get_rag_status():
    """Return real-time RAG engine status from the new rag.manager.

    Falls back to env-only status if the manager is not yet bootstrapped.
    """
    try:
        from rag.bootstrap import bootstrap
        bootstrap()
        from rag.core.manager import manager
        status = manager.get_status()
        return status.to_api_dict()
    except Exception:
        # Fallback: return env-based status
        from app.config import settings
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
            "documents_count": 0,
            "chunks_count": 0,
            "index_ready": False,
            "last_index_time": None,
            "last_query_time": None,
            "last_eval_time": None,
            "last_eval_score": None,
            "health": "fallback",
            "warnings": ["Using fallback status — rag.manager not bootstrapped"],
            # Legacy fields
            "RAG_ENGINE": os.getenv("RAG_ENGINE", "rag_lab"),
            "CHUNK_STRATEGY": os.getenv("CHUNK_STRATEGY") or settings.CHUNK_STRATEGY,
            "RAG_RETRIEVAL_MODE": os.getenv("RAG_RETRIEVAL_MODE", "hybrid"),
            "RAG_HYBRID_FUSION": os.getenv("RAG_HYBRID_FUSION", "rrf"),
            "RAG_USE_RERANK": os.getenv("RAG_USE_RERANK", "false").lower() in {"1", "true"},
            "RAG_RERANK_TOP_N": int(os.getenv("RAG_RERANK_TOP_N", "5")),
        }
