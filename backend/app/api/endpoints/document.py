import os
import uuid
import asyncio
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Depends
from app.models.document import DocumentResponse, DocumentStatusResponse
from app.services.ingestion_service import IngestionService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.core.exceptions import NotFoundException, ValidationException
from app.config import settings

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx", ".doc"}
MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


def _write_file(path: str, content: bytes) -> None:
    with open(path, "wb") as f:
        f.write(content)


def get_ingestion_service() -> IngestionService:
    return IngestionService()


def get_kb_service() -> KnowledgeBaseService:
    return KnowledgeBaseService()


@router.post("/upload", response_model=list[DocumentResponse])
async def upload_documents(
    kb_id: str,
    files: list[UploadFile] = File(...),
    kb_service: KnowledgeBaseService = Depends(get_kb_service),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
):
    kb = await kb_service.get_by_id(kb_id)
    if not kb:
        raise NotFoundException("Knowledge base", kb_id)

    from app.db.sqlite_database import get_database
    db = await get_database()
    kb_dir = os.path.join(settings.UPLOAD_DIR, kb_id)
    await asyncio.get_event_loop().run_in_executor(None, lambda: os.makedirs(kb_dir, exist_ok=True))

    async def _process_one(file: UploadFile) -> dict:
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValidationException(f"Unsupported file type: {ext}")

        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise ValidationException(f"File too large: {file.filename}. Max {settings.MAX_UPLOAD_SIZE_MB}MB")

        doc_id = uuid.uuid4().hex[:12]
        stored_name = f"{doc_id}_{file.filename}"
        file_path = os.path.join(kb_dir, stored_name)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _write_file, file_path, content)

        now = datetime.utcnow().isoformat()
        await db.execute(
            "INSERT INTO documents (id, kb_id, filename, file_type, file_size, file_path, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)",
            (doc_id, kb_id, file.filename, ext.lstrip("."), len(content), file_path, now, now),
        )
        await db.commit()

        asyncio.ensure_future(
            ingestion_service.ingest_document(kb_id, doc_id, file_path, ext, file.filename or "unknown")
        )

        return {
            "id": doc_id, "kb_id": kb_id, "filename": file.filename,
            "file_type": ext.lstrip("."), "file_size": len(content),
            "status": "pending", "chunk_count": 0, "created_at": now,
        }

    docs = await asyncio.gather(*[_process_one(f) for f in files])
    return docs


@router.get("", response_model=list[DocumentResponse])
async def list_documents(kb_id: str, kb_service: KnowledgeBaseService = Depends(get_kb_service)):
    kb = await kb_service.get_by_id(kb_id)
    if not kb:
        raise NotFoundException("Knowledge base", kb_id)

    from app.db.sqlite_database import get_database
    db = await get_database()
    cursor = await db.execute(
        "SELECT * FROM documents WHERE kb_id = ? ORDER BY created_at DESC", (kb_id,)
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


@router.get("/{doc_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(kb_id: str, doc_id: str):
    from app.db.sqlite_database import get_database
    db = await get_database()
    cursor = await db.execute("SELECT status, chunk_count, error_message FROM documents WHERE id = ? AND kb_id = ?", (doc_id, kb_id))
    row = await cursor.fetchone()
    if not row:
        raise NotFoundException("Document", doc_id)
    return {"status": row[0], "chunk_count": row[1] or 0, "error_message": row[2]}


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    kb_id: str,
    doc_id: str,
    ingestion_service: IngestionService = Depends(get_ingestion_service),
):
    from app.db.sqlite_database import get_database
    db = await get_database()
    cursor = await db.execute("SELECT filename, file_path FROM documents WHERE id = ? AND kb_id = ?", (doc_id, kb_id))
    row = await cursor.fetchone()
    if not row:
        raise NotFoundException("Document", doc_id)
    await ingestion_service.delete_document_data(kb_id, doc_id, row[0], row[1])
