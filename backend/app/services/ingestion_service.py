import os
import asyncio
import logging
import traceback
from datetime import datetime
from app.config import settings

logger = logging.getLogger(__name__)


class IngestionService:
    async def ingest_document(self, kb_id: str, doc_id: str, file_path: str, file_ext: str, filename: str) -> None:
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

            # Embedding runs in thread pool internally (via embedding_service)
            embeddings = await embedding_service.embed_documents(texts)

            # Milvus operations
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
            )

            await db.execute(
                "UPDATE documents SET status = 'ready', chunk_count = ?, updated_at = ? WHERE id = ?",
                (len(chunks), datetime.utcnow().isoformat(), doc_id),
            )
            await db.commit()

            # Rebuild BM25 index after successful ingestion
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

    async def delete_document_data(self, kb_id: str, doc_id: str, filename: str, file_path: str) -> None:
        from app.db.milvus_client import milvus_client
        from app.db.sqlite_database import get_database

        await milvus_client.delete_document_chunks(kb_id, doc_id)
        if os.path.exists(file_path):
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, os.remove, file_path)

        db = await get_database()
        await db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        await db.commit()

        # Rebuild BM25 index after deletion
        if settings.ENABLE_HYBRID_SEARCH:
            try:
                from app.services.bm25_service import bm25_service
                chunk_count = await bm25_service.build_index(kb_id)
                logger.info(
                    "[Ingestion] BM25 index rebuilt after deletion kb=%s doc=%s chunk_count=%d",
                    kb_id, doc_id, chunk_count,
                )
            except Exception as bm25_exc:
                logger.warning(
                    "[Ingestion] BM25 rebuild failed after deletion kb=%s doc=%s: %s",
                    kb_id, doc_id, bm25_exc,
                )
