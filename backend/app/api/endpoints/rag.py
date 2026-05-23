import os

from fastapi import APIRouter

from app.config import settings

router = APIRouter()


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _parse_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


@router.get("/status")
async def get_rag_status():
    return {
        "RAG_ENGINE": os.getenv("RAG_ENGINE", "rag_lab"),
        "CHUNK_STRATEGY": os.getenv("CHUNK_STRATEGY") or settings.CHUNK_STRATEGY,
        "RAG_RETRIEVAL_MODE": os.getenv("RAG_RETRIEVAL_MODE", "hybrid"),
        "RAG_HYBRID_FUSION": os.getenv("RAG_HYBRID_FUSION", "rrf"),
        "RAG_USE_RERANK": _parse_bool(os.getenv("RAG_USE_RERANK"), settings.ENABLE_RERANKER),
        "RAG_RERANK_TOP_N": _parse_int(os.getenv("RAG_RERANK_TOP_N"), settings.RERANKER_TOP_N),
    }
