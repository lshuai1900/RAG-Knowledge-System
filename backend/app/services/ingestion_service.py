import os
import asyncio
import logging
import traceback
from datetime import datetime
from app.config import settings

logger = logging.getLogger(__name__)


def _resolve_rag_engine() -> str:
    engine = os.getenv("RAG_ENGINE", "rag_lab").strip().lower()
    return "rag_lab" if engine not in {"rag_lab", "legacy"} else engine


class IngestionService:
    async def ingest_document(self, kb_id: str, doc_id: str, file_path: str, file_ext: str, filename: str) -> None:
        if _resolve_rag_engine() == "rag_lab":
            from app.services.rag_lab_adapter_service import RagLabAdapterService
            await RagLabAdapterService().ingest_document(kb_id, doc_id, file_path, file_ext, filename)
            return

        from app.db.sqlite_database import get_database
        from app.services.document_service import DocumentService
        from app.services.embedding_service import embedding_service
        from app.db.milvus_client import milvus_client

        db = await get_database()
        try:
            await db.execute("UPDATE documents SET status = 'processing', updated_at = ? WHERE id = ?",
                             (datetime.utcnow().isoformat(), doc_id))
            await db.commit()

            doc_service = DocumentService(chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP)
            chunks = await doc_service.load_and_chunk(file_path, file_ext, doc_id=doc_id, filename=filename)

            if not chunks:
                raise ValueError("Document produced no chunks")

            texts = [chunk.page_content for chunk in chunks]
            chunk_indices = [chunk.metadata.get("chunk_index", i) for i, chunk in enumerate(chunks)]
            section_titles = [chunk.metadata.get("section_title", "") for chunk in chunks]
            section_paths = [chunk.metadata.get("section_path", "") for chunk in chunks]
            pages = [chunk.metadata.get("page") for chunk in chunks]
            chunk_strategies = [chunk.metadata.get("chunk_strategy", "recursive") for chunk in chunks]

            embeddings = await embedding_service.embed_documents(texts)

            await milvus_client.insert_chunks(
                kb_id=kb_id,
                texts=texts,
                embeddings=embeddings,
                document_name=filename,
                chunk_indices=chunk_indices,
                doc_id=doc_id,
                section_titles=section_titles,
                section_paths=section_paths,
                pages=pages,
                chunk_strategies=chunk_strategies,
            )

            await db.execute(
                "UPDATE documents SET status = 'ready', chunk_count = ?, updated_at = ? WHERE id = ?",
                (len(chunks), datetime.utcnow().isoformat(), doc_id),
            )
            await db.commit()

            if settings.ENABLE_HYBRID_SEARCH:
                try:
                    from app.services.bm25_service import bm25_service
                    chunk_count = await bm25_service.build_index(kb_id)
                    logger.info(
                        "[Ingestion] BM25 index rebuilt for kb=%s doc=%s chunk_count=%d",
                        kb_id, doc_id, chunk_count,
                    )
                except Exception as bm25_exc:
                    logger.warning(
                        "[Ingestion] BM25 rebuild failed for kb=%s doc=%s: %s — "
                        "BM25 search will fallback to vector-only",
                        kb_id, doc_id, bm25_exc,
                    )

        except Exception as e:
            traceback.print_exc()
            await db.execute(
                "UPDATE documents SET status = 'failed', error_message = ?, updated_at = ? WHERE id = ?",
                (str(e), datetime.utcnow().isoformat(), doc_id),
            )
            await db.commit()

    async def delete_document_data(self, kb_id: str, doc_id: str, filename: str, file_path: str) -> dict:
        """Delete a document and all its index data.

        Steps:
          1. Delete Milvus chunks (by kb_id + doc_id filter).
          2. Delete on-disk file.
          3. Delete DB record.
          4. Delete BM25 chunks (targeted removal from existing index).

        Returns a result dict suitable for DeleteDocumentResponse.
        """
        if _resolve_rag_engine() == "rag_lab":
            from app.services.rag_lab_adapter_service import RagLabAdapterService
            return await RagLabAdapterService().delete_document_data(kb_id, doc_id, filename, file_path)

        from app.db.milvus_client import milvus_client
        from app.db.sqlite_database import get_database

        result = {
            "success": True,
            "doc_id": doc_id,
            "milvus_deleted": False,
            "bm25_deleted": False,
            "warnings": [],
        }

        logger.info("[Ingestion] Deleting document kb=%s doc=%s filename=%s", kb_id, doc_id, filename)

        # 1. Delete Milvus chunks
        try:
            count = await milvus_client.delete_document_chunks(kb_id, doc_id)
            result["milvus_deleted"] = True
            logger.info("[Ingestion] Milvus delete kb=%s doc=%s count=%d", kb_id, doc_id, count)
        except Exception as exc:
            result["success"] = False
            result["warnings"].append(f"Milvus delete failed: {exc}")
            logger.error("[Ingestion] Milvus delete failed kb=%s doc=%s: %s", kb_id, doc_id, exc)

        # 2. Delete on-disk file
        try:
            if os.path.exists(file_path):
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, os.remove, file_path)
                logger.info("[Ingestion] File deleted: %s", file_path)
        except Exception as exc:
            result["warnings"].append(f"File delete failed: {exc}")
            logger.warning("[Ingestion] File delete failed kb=%s doc=%s: %s", kb_id, doc_id, exc)

        # 3. Delete DB record
        try:
            db = await get_database()
            await db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            await db.commit()
            logger.info("[Ingestion] DB record deleted kb=%s doc=%s", kb_id, doc_id)
        except Exception as exc:
            result["success"] = False
            result["warnings"].append(f"DB delete failed: {exc}")
            logger.error("[Ingestion] DB delete failed kb=%s doc=%s: %s", kb_id, doc_id, exc)

        # 4. Delete BM25 chunks (always cleanup, even if hybrid search is disabled)
        try:
            from app.services.bm25_service import bm25_service
            removed = await bm25_service.delete_document_chunks(kb_id, doc_id)
            result["bm25_deleted"] = True
            logger.info("[Ingestion] BM25 delete kb=%s doc=%s removed=%d", kb_id, doc_id, removed)
        except Exception as exc:
            # Fall back to full rebuild
            logger.warning(
                "[Ingestion] BM25 targeted delete failed kb=%s doc=%s: %s — falling back to full rebuild",
                kb_id, doc_id, exc,
            )
            try:
                from app.services.bm25_service import bm25_service
                chunk_count = await bm25_service.build_index(kb_id)
                result["bm25_deleted"] = True
                logger.info(
                    "[Ingestion] BM25 full rebuild after delete kb=%s doc=%s chunk_count=%d",
                    kb_id, doc_id, chunk_count,
                )
            except Exception as bm25_exc:
                result["warnings"].append(f"BM25 delete failed: {bm25_exc}")
                logger.warning(
                    "[Ingestion] BM25 full rebuild also failed kb=%s doc=%s: %s",
                    kb_id, doc_id, bm25_exc,
                )

        logger.info(
            "[Ingestion] Document deletion complete kb=%s doc=%s success=%s warnings=%d",
            kb_id, doc_id, result["success"], len(result["warnings"]),
        )
        return result

    async def cleanup_orphan_document(self, kb_id: str, doc_id: str) -> dict:
        """Clean up index entries for a document already removed from the DB.

        This handles the idempotent-delete case: the document record is gone
        but residual chunks may still exist in Milvus or BM25.  Returns a
        success result with a warning that the document was already deleted.
        """
        if _resolve_rag_engine() == "rag_lab":
            from app.services.rag_lab_adapter_service import RagLabAdapterService
            return await RagLabAdapterService().cleanup_orphan_document(kb_id, doc_id)

        from app.db.milvus_client import milvus_client

        result = {
            "success": True,
            "doc_id": doc_id,
            "milvus_deleted": False,
            "bm25_deleted": False,
            "warnings": ["Document already deleted from database — cleaned up residual index entries"],
        }

        logger.info("[Ingestion] Cleaning up orphan document kb=%s doc=%s", kb_id, doc_id)

        # Clean Milvus
        try:
            count = await milvus_client.delete_document_chunks(kb_id, doc_id)
            result["milvus_deleted"] = True
            if count > 0:
                logger.info("[Ingestion] Orphan Milvus cleanup kb=%s doc=%s count=%d", kb_id, doc_id, count)
        except Exception as exc:
            result["warnings"].append(f"Milvus orphan cleanup failed: {exc}")
            logger.warning("[Ingestion] Orphan Milvus cleanup failed kb=%s doc=%s: %s", kb_id, doc_id, exc)

        # Clean BM25 (always cleanup)
        try:
            from app.services.bm25_service import bm25_service
            removed = await bm25_service.delete_document_chunks(kb_id, doc_id)
            result["bm25_deleted"] = True
            if removed > 0:
                logger.info("[Ingestion] Orphan BM25 cleanup kb=%s doc=%s removed=%d", kb_id, doc_id, removed)
        except Exception as exc:
            result["warnings"].append(f"BM25 orphan cleanup failed: {exc}")
            logger.warning("[Ingestion] Orphan BM25 cleanup failed kb=%s doc=%s: %s", kb_id, doc_id, exc)

        return result

    async def rebuild_kb_index(self, kb_id: str) -> dict:
        """Rebuild the entire vector and BM25 index for a knowledge base.

        Flow:
          1. Verify KB exists and collect document metadata.
          2. Clear Milvus chunks for this kb_id (without dropping collection).
          3. Clear BM25 index for this kb_id.
          4. Re-process each document: load, chunk, embed, insert to Milvus.
          5. Rebuild BM25 index from Milvus data.
          6. Return summary.

        A single broken document file does NOT abort the whole rebuild.
        """
        if _resolve_rag_engine() == "rag_lab":
            from app.services.rag_lab_adapter_service import RagLabAdapterService
            return await RagLabAdapterService().rebuild_kb_index(kb_id)

        from app.db.sqlite_database import get_database
        from app.db.milvus_client import milvus_client
        from app.services.document_service import DocumentService
        from app.services.embedding_service import embedding_service

        result = {
            "status": "completed",
            "kb_id": kb_id,
            "document_count": 0,
            "success_documents": 0,
            "failed_documents": [],
            "chunk_count": 0,
            "bm25_chunk_count": 0,
            "warnings": [],
        }

        db = await get_database()

        # 1. Collect document metadata
        cursor = await db.execute(
            "SELECT id, filename, file_path, file_type FROM documents WHERE kb_id = ?",
            (kb_id,),
        )
        documents = await cursor.fetchall()
        result["document_count"] = len(documents)

        if not documents:
            logger.info("[Rebuild] kb=%s — no documents, only clearing indexes", kb_id)
        else:
            logger.info("[Rebuild] kb=%s — starting rebuild for %d documents", kb_id, len(documents))

        # 2. Clear Milvus
        try:
            deleted = await milvus_client.delete_knowledge_base_chunks(kb_id)
            logger.info("[Rebuild] kb=%s — cleared %d Milvus chunks", kb_id, deleted)
        except Exception as exc:
            result["warnings"].append(f"Milvus clear failed: {exc}")
            logger.error("[Rebuild] kb=%s — Milvus clear failed: %s", kb_id, exc)
            # Continue anyway — insert will add new chunks

        # 3. Clear BM25
        if settings.ENABLE_HYBRID_SEARCH:
            try:
                from app.services.bm25_service import bm25_service
                await bm25_service.delete_index(kb_id)
                logger.info("[Rebuild] kb=%s — cleared BM25 index", kb_id)
            except Exception as exc:
                result["warnings"].append(f"BM25 clear failed: {exc}")
                logger.warning("[Rebuild] kb=%s — BM25 clear failed: %s", kb_id, exc)

        # 4. Re-process each document
        doc_service = DocumentService(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )
        total_chunks = 0

        for doc in documents:
            doc_id = doc["id"]
            filename = doc["filename"]
            file_path = doc["file_path"]
            file_ext = doc["file_type"]

            try:
                if not file_ext:
                    file_ext = os.path.splitext(file_path)[1]
                # Ensure extension has a leading dot for DocumentService
                if not file_ext.startswith("."):
                    file_ext = f".{file_ext}"

                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"Original file not found: {file_path}")

                # Update status to processing
                await db.execute(
                    "UPDATE documents SET status = 'processing', updated_at = ? WHERE id = ?",
                    (datetime.utcnow().isoformat(), doc_id),
                )
                await db.commit()

                chunks = await doc_service.load_and_chunk(
                    file_path, file_ext,
                    doc_id=doc_id, filename=filename,
                )

                if not chunks:
                    raise ValueError("Document produced no chunks")

                texts = [chunk.page_content for chunk in chunks]
                chunk_indices = [chunk.metadata.get("chunk_index", i) for i, chunk in enumerate(chunks)]
                section_titles = [chunk.metadata.get("section_title", "") for chunk in chunks]
                section_paths = [chunk.metadata.get("section_path", "") for chunk in chunks]
                pages = [chunk.metadata.get("page") for chunk in chunks]
                chunk_strategies = [chunk.metadata.get("chunk_strategy", "recursive") for chunk in chunks]

                embeddings = await embedding_service.embed_documents(texts)

                await milvus_client.insert_chunks(
                    kb_id=kb_id,
                    texts=texts,
                    embeddings=embeddings,
                    document_name=filename,
                    chunk_indices=chunk_indices,
                    doc_id=doc_id,
                    section_titles=section_titles,
                    section_paths=section_paths,
                    pages=pages,
                    chunk_strategies=chunk_strategies,
                )

                await db.execute(
                    "UPDATE documents SET status = 'ready', chunk_count = ?, error_message = NULL, updated_at = ? WHERE id = ?",
                    (len(chunks), datetime.utcnow().isoformat(), doc_id),
                )
                await db.commit()

                total_chunks += len(chunks)
                result["success_documents"] += 1
                logger.info(
                    "[Rebuild] kb=%s doc=%s filename=%s chunks=%d OK",
                    kb_id, doc_id, filename, len(chunks),
                )

            except Exception as exc:
                result["failed_documents"].append({
                    "doc_id": doc_id,
                    "filename": filename,
                    "error": str(exc),
                })
                await db.execute(
                    "UPDATE documents SET status = 'failed', error_message = ?, updated_at = ? WHERE id = ?",
                    (str(exc), datetime.utcnow().isoformat(), doc_id),
                )
                await db.commit()
                logger.error(
                    "[Rebuild] kb=%s doc=%s filename=%s FAILED: %s",
                    kb_id, doc_id, filename, exc,
                )

        result["chunk_count"] = total_chunks
        if result["failed_documents"]:
            result["status"] = "partial" if result["success_documents"] > 0 else "failed"

        # 5. Rebuild BM25
        if settings.ENABLE_HYBRID_SEARCH:
            try:
                from app.services.bm25_service import bm25_service
                result["bm25_chunk_count"] = await bm25_service.build_index(kb_id)
                logger.info(
                    "[Rebuild] kb=%s — BM25 rebuilt chunk_count=%d",
                    kb_id, result["bm25_chunk_count"],
                )
            except Exception as exc:
                result["warnings"].append(f"BM25 rebuild failed: {exc}")
                logger.error("[Rebuild] kb=%s — BM25 rebuild failed: %s", kb_id, exc)

        logger.info(
            "[Rebuild] kb=%s complete status=%s docs=%d/%d chunks=%d bm25=%d warnings=%d",
            kb_id, result["status"],
            result["success_documents"], result["document_count"],
            result["chunk_count"], result["bm25_chunk_count"],
            len(result["warnings"]),
        )
        return result
