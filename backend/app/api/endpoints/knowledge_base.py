from fastapi import APIRouter, Depends
from app.models.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate, KnowledgeBaseResponse
from app.services.knowledge_base_service import KnowledgeBaseService
from app.core.exceptions import NotFoundException

router = APIRouter()


def get_kb_service() -> KnowledgeBaseService:
    return KnowledgeBaseService()


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


@router.delete("/{kb_id}", status_code=204)
async def delete_kb(kb_id: str, service: KnowledgeBaseService = Depends(get_kb_service)):
    kb = await service.get_by_id(kb_id)
    if not kb:
        raise NotFoundException("Knowledge base", kb_id)
    await service.delete(kb_id)
