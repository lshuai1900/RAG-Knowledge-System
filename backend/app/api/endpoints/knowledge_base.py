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
    ingestion_service: IngestionService = Depends(get_ingestion_service),
):
    """Rebuild the entire vector and BM25 index for a knowledge base.

    Re-processes all original documents: parse, chunk, embed, insert to
    Milvus, and rebuild BM25.  Documents whose original files are missing
    are reported in failed_documents without aborting the whole rebuild.
    """
    kb = await kb_service.get_by_id(kb_id)
    if not kb:
        raise NotFoundException("Knowledge base", kb_id)
    return await ingestion_service.rebuild_kb_index(kb_id)


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
