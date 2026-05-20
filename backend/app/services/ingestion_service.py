import os
import asyncio
import traceback
from datetime import datetime
from app.config import settings


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
            chunks = await doc_service.load_and_chunk(file_path, file_ext)

            if not chunks:
                raise ValueError("Document produced no chunks")

            texts = [chunk.page_content for chunk in chunks]
            chunk_indices = [chunk.metadata.get("chunk_index", i) for i, chunk in enumerate(chunks)]

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
            )

            await db.execute(
                "UPDATE documents SET status = 'ready', chunk_count = ?, updated_at = ? WHERE id = ?",
                (len(chunks), datetime.utcnow().isoformat(), doc_id),
            )
            await db.commit()

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
