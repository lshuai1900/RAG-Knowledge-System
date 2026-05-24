"""Document endpoints — now routed through rag.service (Yuxi-style).

Upload, list, and delete all delegate to rag.service / KnowledgeBaseManager.
Legacy ingestion_service is kept only as delete fallback.
"""

import os
import uuid
import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Depends

from app.models.document import (
    DocumentResponse, DocumentStatusResponse, DeleteDocumentResponse,
)
from app.services.knowledge_base_service import KnowledgeBaseService
from app.core.exceptions import NotFoundException, ValidationException
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx", ".doc"}
MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


def _write_file(path: str, content: bytes) -> None:
    with open(path, "wb") as f:
        f.write(content)


def get_kb_service() -> KnowledgeBaseService:
    return KnowledgeBaseService()


# ── Upload (new rag.service path) ─────────────────────────────────

@router.post("/upload", response_model=list[DocumentResponse])
async def upload_documents(
    kb_id: str,
    files: list[UploadFile] = File(...),
    kb_service: KnowledgeBaseService = Depends(get_kb_service),
):
    kb = await kb_service.get_by_id(kb_id)
    if not kb:
        raise NotFoundException("Knowledge base", kb_id)

    from app.db.sqlite_database import get_database
    db = await get_database()
    kb_dir = os.path.join(settings.UPLOAD_DIR, kb_id)
    await asyncio.get_event_loop().run_in_executor(
        None, lambda: os.makedirs(kb_dir, exist_ok=True))

    async def _process_one(file: UploadFile) -> dict:
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValidationException(f"Unsupported file type: {ext}")

        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise ValidationException(
                f"File too large: {file.filename}. Max {settings.MAX_UPLOAD_SIZE_MB}MB")

        doc_id = uuid.uuid4().hex[:12]
        stored_name = f"{doc_id}_{file.filename}"
        file_path = os.path.join(kb_dir, stored_name)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _write_file, file_path, content)

        now = datetime.utcnow().isoformat()
        await db.execute(
            "INSERT INTO documents (id, kb_id, filename, file_type, file_size, "
            "file_path, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)",
            (doc_id, kb_id, file.filename, ext.lstrip("."),
             len(content), file_path, now, now),
        )
        await db.commit()

        # Use rag.service for the full ingestion pipeline
        try:
            from rag.service import rag_service
            result = await rag_service.upload_document(
                kb_id, file_path, file.filename or "unknown")
            await db.execute(
                "UPDATE documents SET status = ?, chunk_count = ?, updated_at = ? WHERE id = ?",
                (result.get("status", "ready"),
                 result.get("chunk_count", 0),
                 datetime.utcnow().isoformat(), doc_id),
            )
            await db.commit()
            logger.info("[Upload] doc=%s status=%s chunks=%d via rag.service",
                        doc_id, result.get("status"), result.get("chunk_count", 0))
        except Exception as exc:
            logger.exception("[Upload] rag.service failed for doc=%s", doc_id)
            await db.execute(
                "UPDATE documents SET status = 'failed', error_message = ?, updated_at = ? WHERE id = ?",
                (str(exc), datetime.utcnow().isoformat(), doc_id),
            )
            await db.commit()
            return {
                "id": doc_id, "kb_id": kb_id, "filename": file.filename,
                "file_type": ext.lstrip("."), "file_size": len(content),
                "status": "failed", "error_message": str(exc),
                "chunk_count": 0, "created_at": now,
            }

        return {
            "id": doc_id, "kb_id": kb_id, "filename": file.filename,
            "file_type": ext.lstrip("."), "file_size": len(content),
            "status": result.get("status", "ready"),
            "chunk_count": result.get("chunk_count", 0),
            "chunk_strategy": result.get("chunk_strategy", ""),
            "created_at": now,
        }

    docs = await asyncio.gather(*[_process_one(f) for f in files])
    return docs


# ── List ──────────────────────────────────────────────────────────

@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    kb_id: str,
    kb_service: KnowledgeBaseService = Depends(get_kb_service),
):
    kb = await kb_service.get_by_id(kb_id)
    if not kb:
        raise NotFoundException("Knowledge base", kb_id)

    from app.db.sqlite_database import get_database
    db = await get_database()
    cursor = await db.execute(
        "SELECT * FROM documents WHERE kb_id = ? ORDER BY created_at DESC",
        (kb_id,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


# ── Status ────────────────────────────────────────────────────────

@router.get("/{doc_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(kb_id: str, doc_id: str):
    from app.db.sqlite_database import get_database
    db = await get_database()
    cursor = await db.execute(
        "SELECT status, chunk_count, error_message FROM documents "
        "WHERE id = ? AND kb_id = ?", (doc_id, kb_id))
    row = await cursor.fetchone()
    if not row:
        raise NotFoundException("Document", doc_id)
    return {
        "status": row[0], "chunk_count": row[1] or 0,
        "error_message": row[2],
    }


# ── Delete (legacy ingestion_service fallback) ───────────────────

@router.delete("/{doc_id}", response_model=DeleteDocumentResponse)
async def delete_document(kb_id: str, doc_id: str):
    from app.db.sqlite_database import get_database
    from app.services.ingestion_service import IngestionService

    db = await get_database()
    cursor = await db.execute(
        "SELECT filename, file_path FROM documents WHERE id = ? AND kb_id = ?",
        (doc_id, kb_id),
    )
    row = await cursor.fetchone()
    if not row:
        ingestion_service = IngestionService()
        return await ingestion_service.cleanup_orphan_document(kb_id, doc_id)

    ingestion_service = IngestionService()
    return await ingestion_service.delete_document_data(
        kb_id, doc_id, row[0], row[1])
