"""Unified RagService — single entry point for all RAG API endpoints.

Pattern::

    API endpoint → RagService → KnowledgeBaseManager
                                  → ParserRegistry
                                  → ChunkingDispatcher
                                  → EmbeddingProvider
                                  → RetrievalPipeline
                                  → SourceBuilder
                                  → StatusRuntime

All endpoint logic should delegate here.  No business logic in endpoint handlers.
"""

from __future__ import annotations

import logging
from typing import Any

from rag.bootstrap import bootstrap
from rag.core.manager import KnowledgeBaseManager, manager as _default_manager
from rag.core.schemas import RagStatusInfo, SourceRecord
from rag.core.factory import rag_factory, resolve_strategy

logger = logging.getLogger(__name__)

# Ensure components are registered on first import
bootstrap()


class RagService:
    """Thin service layer that delegates to KnowledgeBaseManager."""

    def __init__(self, manager: KnowledgeBaseManager | None = None):
        self.manager = manager or _default_manager

    # ── Knowledge Base ──────────────────────────────────────────────

    def create_kb(self, name: str, description: str = "") -> dict:
        record = self.manager.create_kb(name, description)
        return {"id": record.kb_id, "name": record.name,
                "description": record.description,
                "document_count": record.document_count,
                "chunk_count": record.chunk_count,
                "created_at": record.created_at,
                "updated_at": record.updated_at}

    def get_kb(self, kb_id: str) -> dict:
        record = self.manager.get_kb(kb_id)
        return {"id": record.kb_id, "name": record.name,
                "description": record.description,
                "document_count": record.document_count,
                "chunk_count": record.chunk_count,
                "created_at": record.created_at,
                "updated_at": record.updated_at}

    def list_kbs(self) -> list[dict]:
        return [{"id": r.kb_id, "name": r.name,
                 "description": r.description,
                 "document_count": r.document_count,
                 "chunk_count": r.chunk_count,
                 "created_at": r.created_at,
                 "updated_at": r.updated_at}
                for r in self.manager.list_kbs()]

    def delete_kb(self, kb_id: str) -> dict:
        self.manager.delete_kb(kb_id)
        return {"success": True, "kb_id": kb_id}

    # ── Document ────────────────────────────────────────────────────

    async def upload_document(self, kb_id: str, file_path: str,
                              filename: str = "") -> dict:
        record = await self.manager.upload_document(kb_id, file_path, filename)
        # Trigger chunk + index
        try:
            chunks = await self.manager.chunk_document(
                kb_id, record.doc_id, file_path, filename)
            await self.manager.build_index(kb_id, [record.doc_id])
            return {"id": record.doc_id, "kb_id": kb_id,
                    "filename": record.filename,
                    "file_type": record.file_type,
                    "file_size": record.file_size,
                    "status": "ready",
                    "chunk_count": len(chunks),
                    "chunk_strategy": chunks[0].chunk_strategy if chunks else "",
                    "created_at": record.created_at}
        except Exception as exc:
            logger.exception("Chunk/index failed for doc %s", record.doc_id)
            return {"id": record.doc_id, "kb_id": kb_id,
                    "filename": record.filename,
                    "file_type": record.file_type,
                    "file_size": record.file_size,
                    "status": "failed",
                    "error_message": str(exc),
                    "chunk_count": 0,
                    "created_at": record.created_at}

    def list_documents(self, kb_id: str) -> list[dict]:
        try:
            chunks = self.manager._load_chunks(kb_id)
        except Exception:
            chunks = []
        return [{"id": c.doc_id, "kb_id": kb_id,
                 "filename": c.filename,
                 "chunk_count": len(chunks),
                 "status": "ready"}
                for c in chunks[:1] or []]

    # ── Query ───────────────────────────────────────────────────────

    async def query(self, kb_id: str, query_text: str,
                    top_k: int = 5) -> dict[str, Any]:
        results = await self.manager.search(kb_id, query_text, top_k)
        chunks = self.manager._load_chunks(kb_id)
        sources = self.manager.build_sources(results, chunks)

        # Build simple context-based answer
        context_texts = [s.content for s in sources if s.content]
        if context_texts:
            answer = f"找到 {len(context_texts)} 个相关片段：\n\n" + \
                     "\n\n---\n\n".join(ctx[:300] for ctx in context_texts[:3])
        else:
            answer = "未找到相关文档内容，请尝试更换问题或上传相关文档。"

        return {
            "answer": answer,
            "sources": [s.to_api_dict() for s in sources],
            "contexts": context_texts,
            "score": max((s.score for s in sources), default=0.0),
            "metadata": {"engine": "rag"},
        }

    # ── Rebuild Index ──────────────────────────────────────────────

    async def rebuild_index(self, kb_id: str) -> dict[str, Any]:
        """Rebuild index for all documents in a KB via the Yuxi-style manager."""
        self.manager._ensure_loaded(kb_id)
        _, chunk_store, vector_store = self._get_stores()

        # Gather all known documents
        docs_dir = self.manager.data_dir / kb_id / "docs"
        if not docs_dir.exists():
            return {"status": "completed", "document_count": 0,
                    "success_documents": 0, "failed_documents": [],
                    "chunk_count": 0, "warnings": ["No documents found"]}

        doc_files = list(docs_dir.glob("*.json"))
        if not doc_files:
            return {"status": "completed", "document_count": 0,
                    "success_documents": 0, "failed_documents": [],
                    "chunk_count": 0, "warnings": ["No document metadata found"]}

        import json
        success = 0
        failed = []
        total_chunks = 0

        for df in doc_files:
            try:
                data = json.loads(df.read_text())
                file_path = data.get("file_path", "")
                filename = data.get("filename", "")
                doc_id = data.get("doc_id", df.stem)

                if not file_path or not Path(file_path).exists():
                    failed.append({"doc_id": doc_id, "filename": filename,
                                   "error": f"File not found: {file_path}"})
                    continue

                chunks = await self.manager.chunk_document(
                    kb_id, doc_id, file_path, filename)
                total_chunks += len(chunks)
                success += 1
            except Exception as exc:
                failed.append({"doc_id": df.stem, "filename": "",
                               "error": str(exc)})

        if success > 0:
            await self.manager.build_index(kb_id)

        status = "completed"
        if failed and success == 0:
            status = "failed"
        elif failed:
            status = "partial"

        return {
            "status": status, "document_count": len(doc_files),
            "success_documents": success, "failed_documents": failed,
            "chunk_count": total_chunks, "warnings": [],
        }

    def _get_stores(self):
        from rag.storage.document_store import DocumentStore, ChunkStore, VectorStore
        from pathlib import Path
        return DocumentStore(self.manager.data_dir), \
               ChunkStore(self.manager.data_dir), \
               VectorStore(self.manager.data_dir)

    # ── Status ──────────────────────────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        return self.manager.get_status().to_api_dict()

    # ── Evaluation ──────────────────────────────────────────────────

    def run_evaluation(self, kb_id: str,
                       dataset: list[dict] | None = None) -> dict[str, Any]:
        """Minimal evaluation — generates a basic report.

        Full Ragas evaluation can be added later via rag/evaluation/.
        """
        import json
        from datetime import datetime, timezone
        from pathlib import Path

        questions = dataset or [
            {"id": "q1", "question": "系统支持哪些分块策略？",
             "ground_truth": "recursive, markdown_header, sentence_window, paragraph"},
            {"id": "q2", "question": "检索流程是什么？",
             "ground_truth": "Dense → Sparse → Fusion → Rerank → Answer"},
        ]

        report_path = Path(self.manager.data_dir) / "eval_reports"
        report_path.mkdir(parents=True, exist_ok=True)
        report_file = report_path / "latest_eval.json"

        results = []
        for q in questions:
            results.append({
                "id": q.get("id"), "question": q.get("question"),
                "ground_truth": q.get("ground_truth", ""), "answer": "",
                "metrics": {"hit_at_k": None, "recall_at_k": None, "mrr": None},
                "note": "Evaluation generated with placeholder metrics. Full Ragas eval requires LLM API key and ragas package.",
            })

        report = {
            "run_name": f"eval_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_questions": len(results),
            "summary": {"hit_at_k": None, "recall_at_k": None, "mrr": None,
                        "faithfulness": None, "answer_relevancy": None},
            "results": results,
            "ragas_error": "Ragas disabled — configure LLM_API_KEY and install ragas for full evaluation.",
        }
        report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        logger.info("Eval report saved to %s", report_file)
        return report


# Module-level service instance
rag_service = RagService()
