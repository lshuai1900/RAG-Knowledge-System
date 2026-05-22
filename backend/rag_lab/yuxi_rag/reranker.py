from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


async def rerank_if_available(query: str, results: list[dict[str, Any]], use_reranker: bool = False) -> list[dict[str, Any]]:
    if not use_reranker or not results:
        return results

    try:
        from app.services.reranker_service import reranker_service
    except Exception:
        return results

    if not getattr(reranker_service, "enabled", False):
        return results

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
        return results

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
    return reordered
