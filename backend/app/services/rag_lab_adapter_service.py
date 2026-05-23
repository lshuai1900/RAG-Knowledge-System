from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator

from app.config import settings
from app.db.sqlite_database import get_database
from app.services.chat_history_service import ChatHistoryService

BACKEND_DIR = Path(__file__).resolve().parents[2]
RAG_LAB_DIR = BACKEND_DIR / "rag_lab"
RAG_LAB_DOCS_DIR = RAG_LAB_DIR / "data" / "docs"
RAG_LAB_CHUNKS_PATH = RAG_LAB_DIR / "data" / "chunks" / "chunks.json"
RAG_LAB_INDEX_DIR = RAG_LAB_DIR / "data" / "index"

for candidate in (BACKEND_DIR, RAG_LAB_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from yuxi_rag import pipeline  # noqa: E402
from yuxi_rag.chunker import save_chunks  # noqa: E402
from yuxi_rag.generator import AnswerGenerator  # noqa: E402
from yuxi_rag.loader import load_documents  # noqa: E402
from yuxi_rag.reranker import rerank_if_available  # noqa: E402
from yuxi_rag.retriever import Retriever  # noqa: E402
from yuxi_rag.vector_store import LocalVectorStore  # noqa: E402

logger = logging.getLogger(__name__)
_index_lock = asyncio.Lock()

_INSUFFICIENT_ANSWER = (
    "当前知识库中没有找到足够相关的资料，无法基于现有文档回答该问题。"
    "建议补充相关文档或换一种问法。"
)


class RagLabAdapterService:
    def __init__(self):
        self.history_service = ChatHistoryService()
        self.max_history_turns = settings.MAX_HISTORY_TURNS
        self.score_threshold = settings.SIMILARITY_SCORE_THRESHOLD
        self.min_source_count = settings.MIN_SOURCE_COUNT
        self.answer_without_source = settings.ANSWER_WITHOUT_SOURCE
        env_rerank = os.getenv("RAG_USE_RERANK")
        if env_rerank is None:
            self.enable_reranker = settings.ENABLE_RERANKER
        else:
            self.enable_reranker = env_rerank.strip().lower() in {"1", "true", "yes", "y"}
        self.reranker_top_k = settings.RERANKER_TOP_K
        self.reranker_top_n = int(os.getenv("RAG_RERANK_TOP_N", settings.RERANKER_TOP_N))
        self.answer_generator = AnswerGenerator()

    def _copied_name(self, kb_id: str, doc_id: str, filename: str) -> str:
        return f"{kb_id}_{doc_id}_{Path(filename).name}"

    def _source_prefix(self, kb_id: str) -> str:
        return f"{kb_id}_"

    def _doc_source_prefix(self, kb_id: str, doc_id: str) -> str:
        return f"{kb_id}_{doc_id}_"

    def _display_name(self, source: str, kb_id: str | None = None, doc_id: str | None = None) -> str:
        if kb_id and doc_id:
            prefix = self._doc_source_prefix(kb_id, doc_id)
            if source.startswith(prefix):
                return source[len(prefix):]
        if kb_id and source.startswith(self._source_prefix(kb_id)):
            parts = source.split("_", 2)
            if len(parts) == 3:
                return parts[2]
        return Path(source).name

    def _parse_source_ids(self, source: str) -> tuple[str | None, str | None]:
        parts = source.split("_", 2)
        if len(parts) < 3:
            return None, None
        return parts[0], parts[1]

    def _ensure_dirs(self) -> None:
        RAG_LAB_DOCS_DIR.mkdir(parents=True, exist_ok=True)
        RAG_LAB_CHUNKS_PATH.parent.mkdir(parents=True, exist_ok=True)
        RAG_LAB_INDEX_DIR.mkdir(parents=True, exist_ok=True)

    async def _copy_doc(self, kb_id: str, doc_id: str, file_path: str, filename: str) -> Path:
        self._ensure_dirs()
        dest = RAG_LAB_DOCS_DIR / self._copied_name(kb_id, doc_id, filename)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, shutil.copy2, file_path, dest)
        return dest

    async def _remove_copied_docs(self, kb_id: str, doc_id: str | None = None) -> int:
        if not RAG_LAB_DOCS_DIR.exists():
            return 0
        prefix = self._doc_source_prefix(kb_id, doc_id) if doc_id else self._source_prefix(kb_id)
        paths = [p for p in RAG_LAB_DOCS_DIR.iterdir() if p.is_file() and p.name.startswith(prefix)]
        loop = asyncio.get_running_loop()
        for path in paths:
            await loop.run_in_executor(None, os.remove, path)
        return len(paths)

    async def _sync_kb_docs_from_db(self, kb_id: str) -> None:
        db = await get_database()
        cursor = await db.execute(
            "SELECT id, filename, file_path FROM documents WHERE kb_id = ?",
            (kb_id,),
        )
        docs = await cursor.fetchall()
        for doc in docs:
            if os.path.exists(doc["file_path"]):
                dest = RAG_LAB_DOCS_DIR / self._copied_name(kb_id, doc["id"], doc["filename"])
                if not dest.exists():
                    await self._copy_doc(kb_id, doc["id"], doc["file_path"], doc["filename"])

    async def _rebuild_global_index_locked(self) -> dict[str, Any]:
        self._ensure_dirs()
        docs = load_documents(RAG_LAB_DOCS_DIR)
        if not docs:
            save_chunks([], RAG_LAB_CHUNKS_PATH)
            metadata_path = RAG_LAB_INDEX_DIR / "metadata.json"
            embeddings_path = RAG_LAB_INDEX_DIR / "embeddings.npy"
            metadata_path.write_text("[]", encoding="utf-8")
            if embeddings_path.exists():
                embeddings_path.unlink()
            return {"documents": 0, "paragraphs": 0, "chunks": 0, "embedding_dim": 0}

        chunk_strategy = os.getenv("CHUNK_STRATEGY") or settings.CHUNK_STRATEGY or "paragraph"
        if chunk_strategy.strip().lower() == "semantic":
            chunk_strategy = "paragraph"
        chunk_size = int(os.getenv("CHUNK_SIZE", settings.CHUNK_SIZE))
        chunk_overlap = int(os.getenv("CHUNK_OVERLAP", settings.CHUNK_OVERLAP))

        result = await pipeline.build_index(
            docs_dir=RAG_LAB_DOCS_DIR,
            index_dir=RAG_LAB_INDEX_DIR,
            chunks_path=RAG_LAB_CHUNKS_PATH,
            chunk_strategy=chunk_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        return {
            "documents": int(result.get("documents", 0)),
            "paragraphs": int(result.get("paragraphs", 0)),
            "chunks": int(result.get("chunks", 0)),
            "embedding_dim": int(result.get("embedding_dim", 0)),
        }

    def _count_chunks_for_doc(self, kb_id: str, doc_id: str) -> int:
        if not RAG_LAB_CHUNKS_PATH.exists():
            return 0
        rows = json.loads(RAG_LAB_CHUNKS_PATH.read_text(encoding="utf-8"))
        prefix = self._doc_source_prefix(kb_id, doc_id)
        return sum(1 for row in rows if (row.get("metadata") or {}).get("source", "").startswith(prefix))

    def _count_chunks_for_kb(self, kb_id: str) -> int:
        if not RAG_LAB_CHUNKS_PATH.exists():
            return 0
        rows = json.loads(RAG_LAB_CHUNKS_PATH.read_text(encoding="utf-8"))
        prefix = self._source_prefix(kb_id)
        return sum(1 for row in rows if (row.get("metadata") or {}).get("source", "").startswith(prefix))

    async def ingest_document(self, kb_id: str, doc_id: str, file_path: str, file_ext: str, filename: str) -> None:
        db = await get_database()
        try:
            await db.execute(
                "UPDATE documents SET status = 'processing', updated_at = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), doc_id),
            )
            await db.commit()

            async with _index_lock:
                await self._copy_doc(kb_id, doc_id, file_path, filename)
                await self._rebuild_global_index_locked()
                chunk_count = self._count_chunks_for_doc(kb_id, doc_id)

            if chunk_count <= 0:
                raise ValueError("Document produced no chunks")

            await db.execute(
                "UPDATE documents SET status = 'ready', chunk_count = ?, error_message = NULL, updated_at = ? WHERE id = ?",
                (chunk_count, datetime.utcnow().isoformat(), doc_id),
            )
            await db.commit()
        except Exception as exc:
            logger.exception("[RagLab] ingestion failed kb=%s doc=%s", kb_id, doc_id)
            await db.execute(
                "UPDATE documents SET status = 'failed', error_message = ?, updated_at = ? WHERE id = ?",
                (str(exc), datetime.utcnow().isoformat(), doc_id),
            )
            await db.commit()

    async def delete_document_data(self, kb_id: str, doc_id: str, filename: str, file_path: str) -> dict:
        result = {
            "success": True,
            "doc_id": doc_id,
            "milvus_deleted": False,
            "bm25_deleted": False,
            "warnings": ["RAG_ENGINE=rag_lab uses local numpy index; Milvus/BM25 cleanup skipped"],
        }
        db = await get_database()
        async with _index_lock:
            try:
                if os.path.exists(file_path):
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, os.remove, file_path)
                await self._remove_copied_docs(kb_id, doc_id)
                await db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
                await db.commit()
                await self._rebuild_global_index_locked()
            except Exception as exc:
                result["success"] = False
                result["warnings"].append(f"rag_lab delete failed: {exc}")
                logger.exception("[RagLab] delete failed kb=%s doc=%s", kb_id, doc_id)
        return result

    async def cleanup_orphan_document(self, kb_id: str, doc_id: str) -> dict:
        result = {
            "success": True,
            "doc_id": doc_id,
            "milvus_deleted": False,
            "bm25_deleted": False,
            "warnings": [
                "Document already deleted from database — cleaned up rag_lab copied docs",
                "RAG_ENGINE=rag_lab uses local numpy index; Milvus/BM25 cleanup skipped",
            ],
        }
        async with _index_lock:
            try:
                await self._remove_copied_docs(kb_id, doc_id)
                await self._rebuild_global_index_locked()
            except Exception as exc:
                result["warnings"].append(f"rag_lab orphan cleanup failed: {exc}")
                logger.exception("[RagLab] orphan cleanup failed kb=%s doc=%s", kb_id, doc_id)
        return result

    async def rebuild_kb_index(self, kb_id: str) -> dict:
        result = {
            "status": "completed",
            "kb_id": kb_id,
            "document_count": 0,
            "success_documents": 0,
            "failed_documents": [],
            "chunk_count": 0,
            "bm25_chunk_count": 0,
            "warnings": ["RAG_ENGINE=rag_lab rebuild rewrites the global local numpy index"],
        }
        db = await get_database()
        cursor = await db.execute(
            "SELECT id, filename, file_path FROM documents WHERE kb_id = ?",
            (kb_id,),
        )
        documents = await cursor.fetchall()
        result["document_count"] = len(documents)

        async with _index_lock:
            await self._remove_copied_docs(kb_id)
            for doc in documents:
                try:
                    await db.execute(
                        "UPDATE documents SET status = 'processing', updated_at = ? WHERE id = ?",
                        (datetime.utcnow().isoformat(), doc["id"]),
                    )
                    await db.commit()
                    if not os.path.exists(doc["file_path"]):
                        raise FileNotFoundError(f"Original file not found: {doc['file_path']}")
                    await self._copy_doc(kb_id, doc["id"], doc["file_path"], doc["filename"])
                except Exception as exc:
                    result["failed_documents"].append({
                        "doc_id": doc["id"],
                        "filename": doc["filename"],
                        "error": str(exc),
                    })
                    await db.execute(
                        "UPDATE documents SET status = 'failed', error_message = ?, updated_at = ? WHERE id = ?",
                        (str(exc), datetime.utcnow().isoformat(), doc["id"]),
                    )
                    await db.commit()

            try:
                await self._rebuild_global_index_locked()
            except Exception as exc:
                result["status"] = "failed"
                result["warnings"].append(f"rag_lab rebuild failed: {exc}")
                for doc in documents:
                    await db.execute(
                        "UPDATE documents SET status = 'failed', error_message = ?, updated_at = ? WHERE id = ?",
                        (str(exc), datetime.utcnow().isoformat(), doc["id"]),
                    )
                await db.commit()
                return result

            for doc in documents:
                if any(item["doc_id"] == doc["id"] for item in result["failed_documents"]):
                    continue
                chunk_count = self._count_chunks_for_doc(kb_id, doc["id"])
                if chunk_count > 0:
                    result["success_documents"] += 1
                    result["chunk_count"] += chunk_count
                    await db.execute(
                        "UPDATE documents SET status = 'ready', chunk_count = ?, error_message = NULL, updated_at = ? WHERE id = ?",
                        (chunk_count, datetime.utcnow().isoformat(), doc["id"]),
                    )
                else:
                    result["failed_documents"].append({
                        "doc_id": doc["id"],
                        "filename": doc["filename"],
                        "error": "Document produced no chunks",
                    })
                    await db.execute(
                        "UPDATE documents SET status = 'failed', error_message = ?, updated_at = ? WHERE id = ?",
                        ("Document produced no chunks", datetime.utcnow().isoformat(), doc["id"]),
                    )
            await db.commit()

        if result["failed_documents"]:
            result["status"] = "partial" if result["success_documents"] > 0 else "failed"
        return result

    async def cleanup_knowledge_base(self, kb_id: str) -> int:
        async with _index_lock:
            count = await self._remove_copied_docs(kb_id)
            await self._rebuild_global_index_locked()
            return count

    async def get_index_status(self, kb_id: str) -> dict:
        db = await get_database()
        cursor = await db.execute(
            "SELECT status, COUNT(*) FROM documents WHERE kb_id = ? GROUP BY status",
            (kb_id,),
        )
        rows = await cursor.fetchall()
        documents_by_status = {row[0]: row[1] for row in rows}
        return {
            "kb_id": kb_id,
            "document_count": sum(documents_by_status.values()),
            "chunk_count": self._count_chunks_for_kb(kb_id),
            "bm25_chunk_count": 0,
            "bm25_index_exists": False,
            "documents_by_status": documents_by_status,
        }

    async def _retrieve(self, kb_id: str, query: str) -> list[dict[str, Any]]:
        store = LocalVectorStore(RAG_LAB_INDEX_DIR)
        if not store.exists():
            return []
        retrieval_mode = os.getenv("RAG_RETRIEVAL_MODE", "hybrid").strip().lower()
        fusion = os.getenv("RAG_HYBRID_FUSION", "rrf").strip().lower()
        dense_weight = float(os.getenv("RAG_HYBRID_DENSE_WEIGHT", "0.7"))
        sparse_weight = float(os.getenv("RAG_HYBRID_SPARSE_WEIGHT", "0.3"))

        top_k = self.reranker_top_k if self.enable_reranker else settings.TOP_K
        recall_k = max(top_k * 5, self.reranker_top_k, settings.TOP_K)
        retriever = Retriever(index_dir=RAG_LAB_INDEX_DIR)
        try:
            results = await retriever.retrieve(
                query,
                top_k=recall_k,
                retrieval_mode=retrieval_mode,
                fusion=fusion,
                dense_weight=dense_weight,
                sparse_weight=sparse_weight,
            )
        except Exception as exc:
            logger.warning("[RagLab] retrieval fallback to vector mode: %s", exc)
            results = await retriever.retrieve(
                query,
                top_k=recall_k,
                retrieval_mode="vector",
                fusion=fusion,
                dense_weight=dense_weight,
                sparse_weight=sparse_weight,
            )
        prefix = self._source_prefix(kb_id)
        filtered = [
            result for result in results
            if str((result.get("metadata") or {}).get("source", "")).startswith(prefix)
        ]
        filtered = await rerank_if_available(
            query,
            filtered,
            use_reranker=self.enable_reranker,
            top_n=self.reranker_top_n,
        )
        keep = self.reranker_top_n if self.enable_reranker else settings.TOP_K
        return filtered[:keep]

    def _effective_results(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not results:
            return []
        threshold = 1.0 - self.score_threshold
        return [result for result in results if float(result.get("score") or 0.0) >= threshold]

    def _confidence_decision(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        if not results:
            return {"ok": False, "reason": "no_results", "top_similarity_score": 0.0}
        top_score = max(float(result.get("score") or 0.0) for result in results)
        effective = self._effective_results(results)
        if len(effective) < self.min_source_count:
            return {
                "ok": False,
                "reason": "insufficient_sources",
                "top_similarity_score": top_score,
                "effective_count": len(effective),
            }
        if not self.answer_without_source and not effective:
            return {"ok": False, "reason": "no_relevant_sources", "top_similarity_score": top_score}
        return {"ok": True, "top_similarity_score": top_score, "effective_count": len(effective)}

    def _build_source(self, result: dict[str, Any]) -> dict[str, Any]:
        metadata = dict(result.get("metadata") or {})
        source = str(metadata.get("source", ""))
        kb_id, doc_id = self._parse_source_ids(source)
        score = round(float(result.get("score") or 0.0), 6)
        content = result.get("chunk_text", "") or ""
        metadata.update({"kb_id": kb_id, "doc_id": doc_id, "source": source})
        src = {
            "source": source,
            "document_name": self._display_name(source, kb_id, doc_id),
            "chunk_index": metadata.get("chunk_index", 0),
            "section_title": "",
            "section_path": "",
            "page": metadata.get("page"),
            "score": score,
            "raw_score": round(1.0 - score, 6),
            "similarity_score": score,
            "dense_score": result.get("dense_score"),
            "sparse_score": result.get("sparse_score"),
            "fusion_score": result.get("fusion_score"),
            "chunk_strategy": metadata.get("chunk_strategy"),
            "content": content[:500],
            "content_preview": content[:200],
            "chunk_id": result.get("chunk_id"),
            "metadata": metadata,
        }
        if "rerank_score" in result:
            src["rerank_score"] = result["rerank_score"]
        if "rerank_rank" in result:
            src["rerank_rank"] = result["rerank_rank"]
        return src

    async def _generate_answer(self, query: str, results: list[dict[str, Any]]) -> str:
        payload = await self.answer_generator.generate(query, results)
        return payload.get("answer", "")

    async def query(self, kb_id: str, session_id: str, query: str) -> dict:
        await self.history_service.add_message(session_id, "user", query)
        results = await self._retrieve(kb_id, query)
        decision = self._confidence_decision(results)
        response_metadata = {"engine": "rag_lab", "kb_id": kb_id}
        if not decision["ok"]:
            msg_id = await self.history_service.add_message(session_id, "assistant", _INSUFFICIENT_ANSWER, [])
            return {
                "answer": _INSUFFICIENT_ANSWER,
                "sources": [],
                "contexts": [],
                "score": decision.get("top_similarity_score", 0.0),
                "metadata": response_metadata,
                "message_id": msg_id,
                "confidence": "low",
                "reason": decision["reason"],
                "top_similarity_score": decision.get("top_similarity_score", 0.0),
                "threshold": self.score_threshold,
            }

        effective = self._effective_results(results)
        sources = [self._build_source(result) for result in effective]
        answer = await self._generate_answer(query, effective)
        msg_id = await self.history_service.add_message(session_id, "assistant", answer, sources)
        contexts = [source.get("content", "") for source in sources]
        return {
            "answer": answer,
            "sources": sources,
            "contexts": contexts,
            "score": decision.get("top_similarity_score", 0.0),
            "metadata": response_metadata,
            "message_id": msg_id,
            "top_similarity_score": decision.get("top_similarity_score"),
            "threshold": self.score_threshold,
        }

    async def query_stream(self, kb_id: str, session_id: str, query: str) -> AsyncIterator[dict]:
        await self.history_service.add_message(session_id, "user", query)
        results = await self._retrieve(kb_id, query)
        decision = self._confidence_decision(results)
        response_metadata = {"engine": "rag_lab", "kb_id": kb_id}
        if not decision["ok"]:
            msg_id = await self.history_service.add_message(session_id, "assistant", _INSUFFICIENT_ANSWER, [])
            yield {"type": "chunk", "text": _INSUFFICIENT_ANSWER}
            yield {"type": "sources", "sources": []}
            yield {
                "type": "done",
                "message_id": msg_id,
                "score": decision.get("top_similarity_score", 0.0),
                "metadata": response_metadata,
                "contexts": [],
                "confidence": "low",
                "reason": decision["reason"],
            }
            return

        effective = self._effective_results(results)
        sources = [self._build_source(result) for result in effective]
        answer = await self._generate_answer(query, effective)
        msg_id = await self.history_service.add_message(session_id, "assistant", answer, sources)
        contexts = [source.get("content", "") for source in sources]
        yield {"type": "chunk", "text": answer}
        yield {"type": "sources", "sources": sources}
        yield {
            "type": "done",
            "message_id": msg_id,
            "score": decision.get("top_similarity_score", 0.0),
            "metadata": response_metadata,
            "contexts": contexts,
            "top_similarity_score": decision.get("top_similarity_score"),
            "threshold": self.score_threshold,
        }
