"""Retrieval pipeline — dense / sparse / hybrid / fusion / rerank / context.

Unified entry point::

    pipeline = RetrievalPipeline(embedder, chunk_store, vector_store)
    results = await pipeline.retrieve(kb_id, query, top_k=5)
    sources = pipeline.build_sources(results)

All retrieval results flow through this module — no ad-hoc source
construction in endpoints or legacy services.
"""

from .pipeline import RetrievalPipeline
