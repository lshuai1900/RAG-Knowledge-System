from fastapi import APIRouter
from app.api.endpoints import health, knowledge_base, document, chat, rag

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(knowledge_base.router, prefix="/knowledge-bases", tags=["knowledge-bases"])
api_router.include_router(document.router, prefix="/knowledge-bases/{kb_id}/documents", tags=["documents"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
