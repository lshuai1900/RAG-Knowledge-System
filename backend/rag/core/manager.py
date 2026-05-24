"""Yuxi-style KnowledgeBaseManager — single orchestrator for all RAG operations."""

from __future__ import annotations

import dataclasses
import logging
import os
import json
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .schemas import (
    KnowledgeBaseRecord, DocumentRecord, ChunkRecord,
    ParseResult, EmbeddingResult, RetrievalResult, SourceRecord,
    RagStatusInfo,
)
from .factory import rag_factory, resolve_strategy
from .exceptions import (
    ParserNotFoundError, ChunkStrategyError, EmbeddingError,
    IndexNotReadyError, KnowledgeBaseNotFoundError,
)

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]
RAG_DATA_DIR = BACKEND_DIR / "rag" / "data"


class KnowledgeBaseManager:
    """Main entry point for all RAG knowledge base operations."""

    def __init__(self, data_dir: str | Path | None = None):
        self.data_dir = Path(data_dir) if data_dir else RAG_DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._metadata: dict[str, dict] = {}  # kb_id → metadata

    # ── Knowledge Base CRUD ─────────────────────────────────────────

    def create_kb(self, name: str, description: str = "") -> KnowledgeBaseRecord:
        import uuid
        kb_id = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc).isoformat()
        record = KnowledgeBaseRecord(
            kb_id=kb_id, name=name, description=description,
            created_at=now, updated_at=now,
        )
        self._metadata[kb_id] = dataclasses.asdict(record)
        self._save_meta(kb_id, record)
        (self.data_dir / kb_id).mkdir(parents=True, exist_ok=True)
        return record

    def get_kb(self, kb_id: str) -> KnowledgeBaseRecord:
        self._ensure_loaded(kb_id)
        meta = self._metadata.get(kb_id)
        if not meta:
            raise KnowledgeBaseNotFoundError(f"KB {kb_id} not found")
        return KnowledgeBaseRecord(**meta)

    def list_kbs(self) -> list[KnowledgeBaseRecord]:
        self._load_all()
        return [KnowledgeBaseRecord(**m) for m in self._metadata.values()]

    def delete_kb(self, kb_id: str) -> None:
        if kb_id in self._metadata:
            del self._metadata[kb_id]
        kb_dir = self.data_dir / kb_id
        if kb_dir.exists():
            import shutil
            shutil.rmtree(kb_dir)

    # ── Document Upload & Parsing ───────────────────────────────────

    async def upload_document(self, kb_id: str, file_path: str,
                              filename: str = "") -> DocumentRecord:
        self._ensure_loaded(kb_id)
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(str(path))

        fname = filename or path.name
        ext = path.suffix.lower()

        # Parse using registry
        try:
            parse_result = rag_factory.parser_registry.parse(path)
        except ParserNotFoundError:
            raise ParserNotFoundError(f"Unsupported file type: {ext}")

        doc_id = self._make_doc_id(kb_id, fname)
        record = DocumentRecord(
            doc_id=doc_id, kb_id=kb_id, filename=fname,
            file_type=ext.lstrip("."), file_size=path.stat().st_size,
            file_path=str(path), status="parsed",
            chunk_strategy="", created_at=datetime.now(timezone.utc).isoformat(),
            metadata=parse_result.metadata,
        )
        self._save_doc_meta(kb_id, doc_id, record)
        return record

    async def chunk_document(self, kb_id: str, doc_id: str,
                             file_path: str, filename: str = "",
                             strategy: str | None = None) -> list[ChunkRecord]:
        path = Path(file_path)
        ext = path.suffix.lower()
        fname = filename or path.name

        # Parse
        parse_result = rag_factory.parser_registry.parse(path)

        # Resolve strategy
        resolved = resolve_strategy(strategy, ext.lstrip("."))

        # Chunk
        chunker = rag_factory.get_chunker(resolved, ext.lstrip("."))
        chunks = chunker.chunk(parse_result.text, {
            "doc_id": doc_id, "kb_id": kb_id,
            "filename": fname, "file_type": ext.lstrip("."),
            "parser_name": parse_result.parser_name,
        })

        # Save chunks
        self._save_chunks(kb_id, doc_id, chunks)
        return chunks

    async def build_index(self, kb_id: str, doc_ids: list[str] | None = None) -> dict:
        """Build/rebuild vector index for a KB."""
        all_chunks = self._load_chunks(kb_id, doc_ids)
        if not all_chunks:
            return {"chunks": 0, "status": "empty"}

        provider = rag_factory.get_embedding_provider()
        embed_result = await provider.embed(all_chunks)

        # Save embeddings
        emb_path = self.data_dir / kb_id / "embeddings.npy"
        meta_path = self.data_dir / kb_id / "index_meta.json"
        import numpy as np
        arr = np.array(embed_result.embeddings, dtype=np.float32)
        np.save(str(emb_path), arr)
        meta_path.write_text(json.dumps({
            "chunk_ids": [c.chunk_id for c in all_chunks],
            "dimension": provider.dimension,
            "model": provider.model_name,
            "provider": provider.name,
            "chunk_count": len(all_chunks),
            "built_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False, indent=2), encoding="utf-8")

        return {"chunks": len(all_chunks), "status": "built",
                "dimension": provider.dimension}

    # ── Retrieval ───────────────────────────────────────────────────

    async def search(self, kb_id: str, query: str, top_k: int = 5) -> list[RetrievalResult]:
        import numpy as np

        emb_path = self.data_dir / kb_id / "embeddings.npy"
        meta_path = self.data_dir / kb_id / "index_meta.json"
        if not emb_path.exists() or not meta_path.exists():
            raise IndexNotReadyError(f"Index not built for KB {kb_id}")

        provider = rag_factory.get_embedding_provider()
        chunk_records = self._load_chunks(kb_id)

        # Single-query embedding
        query_embedding = await provider._embed_text(query)

        # Cosine similarity search
        embeddings = np.load(str(emb_path))
        query_vec = np.array(query_embedding, dtype=np.float32)
        query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-8)
        emb_norm = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8)
        scores = emb_norm @ query_norm
        top_indices = np.argsort(scores)[::-1][:top_k]

        retrieval_mode = os.getenv("RAG_RETRIEVAL_MODE", "dense")
        fusion = os.getenv("RAG_HYBRID_FUSION", "rrf")

        results = []
        for rank, idx in enumerate(top_indices):
            score = float(scores[idx])
            if score <= 0:
                continue
            chunk = chunk_records[int(idx)] if int(idx) < len(chunk_records) else None
            results.append(RetrievalResult(
                chunk_id=chunk.chunk_id if chunk else f"chunk_{idx}",
                chunk_text=chunk.text if chunk else "",
                score=round(score, 6),
                dense_score=round(score, 6),
                rank=rank + 1,
                retrieval_mode=retrieval_mode,
                hybrid_fusion=fusion if retrieval_mode == "hybrid" else "",
                metadata=chunk.metadata if chunk else {},
            ))

        return results

    def build_sources(self, results: list[RetrievalResult],
                      chunks: list[ChunkRecord]) -> list[SourceRecord]:
        """Build SourceRecord list from retrieval results + chunk metadata."""
        chunk_map: dict[str, ChunkRecord] = {c.chunk_id: c for c in chunks}
        sources = []
        for i, r in enumerate(results):
            chunk = chunk_map.get(r.chunk_id)
            sources.append(SourceRecord(
                document_id=chunk.doc_id if chunk else "",
                filename=chunk.filename if chunk else "",
                chunk_id=r.chunk_id,
                chunk_index=chunk.chunk_index if chunk else 0,
                content=r.chunk_text[:500],
                score=r.score,
                dense_score=r.dense_score,
                sparse_score=r.sparse_score,
                fusion_score=r.fusion_score,
                rerank_score=r.rerank_score,
                retrieval_mode=r.retrieval_mode,
                hybrid_fusion=r.hybrid_fusion,
                chunk_strategy=chunk.chunk_strategy if chunk else "",
                section_title=chunk.section_title if chunk else "",
                section_path=chunk.section_path if chunk else "",
                rank=i + 1,
                metadata=r.metadata,
            ))
        return sources

    # ── Status ──────────────────────────────────────────────────────

    def get_status(self) -> RagStatusInfo:
        provider = rag_factory.get_embedding_provider()
        total_chunks = 0
        all_chunks_ok = True
        for kb_id in self._metadata:
            chunks = self._load_chunks(kb_id)
            total_chunks += len(chunks)
            if not (self.data_dir / kb_id / "embeddings.npy").exists():
                all_chunks_ok = False

        return RagStatusInfo(
            rag_engine=os.getenv("RAG_ENGINE", "rag_lab"),
            embedding_provider=provider.name,
            embedding_model=provider.model_name,
            embedding_dim=provider.dimension,
            index_embedding_dim=provider.dimension,
            chunk_strategy=resolve_strategy(),
            chunk_size=int(os.getenv("CHUNK_SIZE", "800")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "120")),
            chunk_min_size=int(os.getenv("CHUNK_MIN_SIZE", "100")),
            retrieval_mode=os.getenv("RAG_RETRIEVAL_MODE", "hybrid"),
            hybrid_fusion=os.getenv("RAG_HYBRID_FUSION", "rrf"),
            use_rerank=os.getenv("RAG_USE_RERANK", "false").lower() in {"1", "true"},
            rerank_model=os.getenv("RERANKER_MODEL", ""),
            rerank_top_n=int(os.getenv("RAG_RERANK_TOP_N", "5")),
            documents_count=sum(
                len(list((self.data_dir / kb_id / "docs").glob("*.json")))
                if (self.data_dir / kb_id / "docs").exists() else 0
                for kb_id in self._metadata
            ),
            chunks_count=total_chunks,
            index_ready=all_chunks_ok and total_chunks > 0,
            last_index_time=self._read_last_index_time(),
            health="healthy" if all_chunks_ok else "index_missing",
        )

    # ── Internal Helpers ────────────────────────────────────────────

    def _make_doc_id(self, kb_id: str, filename: str) -> str:
        import hashlib
        raw = f"{kb_id}_{filename}_{datetime.now(timezone.utc).timestamp()}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def _ensure_loaded(self, kb_id: str) -> None:
        meta_file = self.data_dir / kb_id / "meta.json"
        if kb_id not in self._metadata and meta_file.exists():
            self._metadata[kb_id] = json.loads(meta_file.read_text())

    def _load_all(self) -> None:
        for d in self.data_dir.iterdir():
            if d.is_dir() and (d / "meta.json").exists():
                self._metadata[d.name] = json.loads((d / "meta.json").read_text())

    def _save_meta(self, kb_id: str, record: KnowledgeBaseRecord) -> None:
        (self.data_dir / kb_id).mkdir(parents=True, exist_ok=True)
        (self.data_dir / kb_id / "meta.json").write_text(
            json.dumps(dataclasses.asdict(record), ensure_ascii=False, indent=2))

    def _save_doc_meta(self, kb_id: str, doc_id: str, record: DocumentRecord) -> None:
        docs_dir = self.data_dir / kb_id / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / f"{doc_id}.json").write_text(
            json.dumps(dataclasses.asdict(record), ensure_ascii=False, indent=2))

    def _save_chunks(self, kb_id: str, doc_id: str, chunks: list[ChunkRecord]) -> None:
        chunks_dir = self.data_dir / kb_id / "chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)
        (chunks_dir / f"{doc_id}.json").write_text(
            json.dumps([c.to_dict() for c in chunks], ensure_ascii=False, indent=2))

    def _load_chunks(self, kb_id: str, doc_ids: list[str] | None = None) -> list[ChunkRecord]:
        chunks_dir = self.data_dir / kb_id / "chunks"
        if not chunks_dir.exists():
            return []
        all_chunks = []
        for f in chunks_dir.glob("*.json"):
            if doc_ids and f.stem not in doc_ids:
                continue
            rows = json.loads(f.read_text())
            for row in rows:
                all_chunks.append(ChunkRecord(**row))
        return all_chunks

    def _read_last_index_time(self) -> str | None:
        for kb_id in self._metadata:
            meta_path = self.data_dir / kb_id / "index_meta.json"
            if meta_path.exists():
                return datetime.fromtimestamp(meta_path.stat().st_mtime).isoformat()
        return None


# Module-level singleton
manager = KnowledgeBaseManager()
