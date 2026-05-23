from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y"}


def _annotate_results(results: list[dict[str, Any]], enabled: bool) -> list[dict[str, Any]]:
    for result in results:
        metadata = dict(result.get("metadata") or {})
        metadata["rerank_enabled"] = enabled
        metadata["original_score"] = result.get("score")
        if "rerank_score" in result:
            metadata["rerank_score"] = result.get("rerank_score")
        result["metadata"] = metadata
    return results


async def rerank_if_available(
    query: str,
    results: list[dict[str, Any]],
    use_reranker: bool = False,
    top_n: int | None = None,
) -> list[dict[str, Any]]:
    if not results:
        return results

    effective_enabled = _env_flag("RAG_USE_RERANK", use_reranker)
    if not effective_enabled:
        return _annotate_results(results, enabled=False)

    try:
        from app.services.reranker_service import reranker_service
    except Exception:
        return _annotate_results(results, enabled=False)

    if not getattr(reranker_service, "enabled", False):
        return _annotate_results(results, enabled=False)

    sources = []
    for result in results:
        metadata = result.get("metadata") or {}
        sources.append({
            "content": result.get("chunk_text", ""),
            "document_name": metadata.get("source", ""),
            "chunk_index": metadata.get("chunk_index", 0),
            "score": result.get("score", 0.0),
            "similarity_score": result.get("score", 0.0),
            **metadata,
        })

    try:
        ranked = await reranker_service.rerank(query, sources)
    except Exception:
        return _annotate_results(results, enabled=False)

    by_key = {
        (item.get("document_name") or item.get("source"), item.get("chunk_index")): item
        for item in ranked
    }
    reordered: list[dict[str, Any]] = []
    used: set[tuple[Any, Any]] = set()
    for result in results:
        metadata = result.get("metadata") or {}
        key = (metadata.get("source"), metadata.get("chunk_index"))
        if key in by_key:
            enriched = dict(result)
            enriched["rerank_score"] = by_key[key].get("rerank_score")
            enriched["rerank_rank"] = by_key[key].get("rerank_rank")
            reordered.append(enriched)
            used.add(key)

    reordered.sort(key=lambda item: item.get("rerank_rank", 10**9))
    for result in results:
        metadata = result.get("metadata") or {}
        key = (metadata.get("source"), metadata.get("chunk_index"))
        if key not in used:
            reordered.append(result)
    if top_n is not None and top_n > 0:
        reordered = reordered[:top_n]
    return _annotate_results(reordered, enabled=True)
