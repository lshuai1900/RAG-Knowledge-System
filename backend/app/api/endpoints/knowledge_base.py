import os

from fastapi import APIRouter, Depends
from app.models.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate, KnowledgeBaseResponse
from app.models.document import (
    DeleteKnowledgeBaseResponse, RebuildIndexResponse, IndexStatusResponse,
)
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.ingestion_service import IngestionService
from app.core.exceptions import NotFoundException

router = APIRouter()


def get_kb_service() -> KnowledgeBaseService:
    return KnowledgeBaseService()


def get_ingestion_service() -> IngestionService:
    return IngestionService()


@router.get("", response_model=list[KnowledgeBaseResponse])
async def list_kb(service: KnowledgeBaseService = Depends(get_kb_service)):
    return await service.list_all()


@router.post("", response_model=KnowledgeBaseResponse, status_code=201)
async def create_kb(data: KnowledgeBaseCreate, service: KnowledgeBaseService = Depends(get_kb_service)):
    return await service.create(data.name, data.description)


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_kb(kb_id: str, service: KnowledgeBaseService = Depends(get_kb_service)):
    kb = await service.get_by_id(kb_id)
    if not kb:
        raise NotFoundException("Knowledge base", kb_id)
    return kb


@router.put("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_kb(kb_id: str, data: KnowledgeBaseUpdate, service: KnowledgeBaseService = Depends(get_kb_service)):
    kb = await service.update(kb_id, data.name, data.description)
    if not kb:
        raise NotFoundException("Knowledge base", kb_id)
    return kb


@router.delete("/{kb_id}", response_model=DeleteKnowledgeBaseResponse)
async def delete_kb(kb_id: str, service: KnowledgeBaseService = Depends(get_kb_service)):
    """Delete a knowledge base and all associated data.

    Cleans up: DB records, Milvus collection, uploaded files, BM25 index,
    and chat sessions/messages.  Returns detailed per-step status.
    """
    kb = await service.get_by_id(kb_id)
    if not kb:
        raise NotFoundException("Knowledge base", kb_id)
    return await service.delete(kb_id)


@router.post("/{kb_id}/rebuild-index", response_model=RebuildIndexResponse)
async def rebuild_index(
    kb_id: str,
    kb_service: KnowledgeBaseService = Depends(get_kb_service),
):
    """Rebuild the entire vector index via rag.service (Yuxi-style).

    All documents in the KB are re-parsed, re-chunked, re-embedded,
    and the vector index is rewritten.  Uses EMBEDDING_PROVIDER from env.
    """
    kb = await kb_service.get_by_id(kb_id)
    if not kb:
        raise NotFoundException("Knowledge base", kb_id)

    try:
        from rag.service import rag_service
        result = await rag_service.rebuild_index(kb_id)
        return {
            "status": result.get("status", "completed"),
            "kb_id": kb_id,
            "document_count": result.get("document_count", 0),
            "success_documents": result.get("success_documents", 0),
            "failed_documents": result.get("failed_documents", []),
            "chunk_count": result.get("chunk_count", 0),
            "bm25_chunk_count": 0,
            "warnings": result.get("warnings", []),
        }
    except Exception as exc:
        logger = __import__("logging").getLogger(__name__)
        logger.exception("rebuild-index via rag.service failed")
        return {
            "status": "failed",
            "kb_id": kb_id,
            "document_count": 0,
            "success_documents": 0,
            "failed_documents": [{"doc_id": "", "filename": "", "error": str(exc)}],
            "chunk_count": 0,
            "bm25_chunk_count": 0,
            "warnings": [str(exc)],
        }


@router.get("/{kb_id}/index-status", response_model=IndexStatusResponse)
async def get_index_status(
    kb_id: str,
    kb_service: KnowledgeBaseService = Depends(get_kb_service),
):
    """Return the current index status for a knowledge base.

    Includes document counts by status, Milvus chunk count, and BM25
    index status.
    """
    kb = await kb_service.get_by_id(kb_id)
    if not kb:
        raise NotFoundException("Knowledge base", kb_id)

    # Prefer rag.service for status; fall back to legacy rag_lab adapter
    try:
        from rag.service import rag_service
        status = rag_service.get_status()
        return {
            "kb_id": kb_id,
            "document_count": status.get("documents_count", 0),
            "chunk_count": status.get("chunks_count", 0),
            "bm25_chunk_count": 0,
            "bm25_index_exists": False,
            "documents_by_status": {},
        }
    except Exception:
        pass
    if os.getenv("RAG_ENGINE", "rag_lab").strip().lower() == "rag_lab":
        from app.services.rag_lab_adapter_service import RagLabAdapterService
        return await RagLabAdapterService().get_index_status(kb_id)

    from app.db.sqlite_database import get_database
    from app.db.milvus_client import milvus_client

    db = await get_database()

    # Document counts by status
    cursor = await db.execute(
        "SELECT status, COUNT(*) FROM documents WHERE kb_id = ? GROUP BY status",
        (kb_id,),
    )
    rows = await cursor.fetchall()
    documents_by_status = {row[0]: row[1] for row in rows}

    # Total document count
    document_count = sum(documents_by_status.values())

    # Milvus chunk count
    try:
        all_chunks = await milvus_client.get_all_chunks(kb_id)
        chunk_count = len(all_chunks)
    except Exception:
        chunk_count = -1  # signal error

    # BM25 status
    bm25_chunk_count = 0
    bm25_index_exists = False
    try:
        from app.services.bm25_service import bm25_service
        bm25_index_exists = await bm25_service.index_exists(kb_id)
        if bm25_index_exists:
            bm25_chunk_count = await bm25_service.get_chunk_count(kb_id)
    except Exception:
        bm25_chunk_count = -1

    return {
        "kb_id": kb_id,
        "document_count": document_count,
        "chunk_count": chunk_count,
        "bm25_chunk_count": bm25_chunk_count,
        "bm25_index_exists": bm25_index_exists,
        "documents_by_status": documents_by_status,
    }
