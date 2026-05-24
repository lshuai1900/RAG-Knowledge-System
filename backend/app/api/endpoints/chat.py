"""Chat endpoints — delegate to rag.service (Yuxi-style).

Legacy RAGService is kept as fallback for backward compatibility with
Milvus / hybrid search paths.  New queries prefer rag.service.
"""

import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.models.chat import (
    SessionCreate, SessionResponse, SessionDetailResponse,
    QueryRequest, QueryResponse,
)
from app.services.chat_history_service import ChatHistoryService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.core.exceptions import NotFoundException, ValidationException

logger = logging.getLogger(__name__)
router = APIRouter()


def get_history_service() -> ChatHistoryService:
    return ChatHistoryService()


def get_kb_service() -> KnowledgeBaseService:
    return KnowledgeBaseService()


async def _validate_query(kb_id: str, session_id: str) -> None:
    kb_service = KnowledgeBaseService()
    kb = await kb_service.get_by_id(kb_id)
    if not kb:
        raise NotFoundException("Knowledge base", kb_id)
    history_service = ChatHistoryService()
    session = await history_service.get_session(session_id)
    if not session:
        raise NotFoundException("Session", session_id)
    if session.get("kb_id") != kb_id:
        raise ValidationException(
            f"Session {session_id} does not belong to knowledge base {kb_id}")


# ── Session CRUD (unchanged) ──────────────────────────────────────

@router.post("/sessions", response_model=SessionResponse, status_code=201)
async def create_session(data: SessionCreate,
                         service: ChatHistoryService = Depends(get_history_service)):
    return await service.create_session(data.kb_id, data.title)


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(kb_id: str | None = None,
                        service: ChatHistoryService = Depends(get_history_service)):
    return await service.list_sessions(kb_id)


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(session_id: str,
                      service: ChatHistoryService = Depends(get_history_service)):
    session = await service.get_session(session_id)
    if not session:
        raise NotFoundException("Session", session_id)
    messages = await service.get_messages(session_id)
    return {"session": session, "messages": messages}


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str,
                         service: ChatHistoryService = Depends(get_history_service)):
    session = await service.get_session(session_id)
    if not session:
        raise NotFoundException("Session", session_id)
    await service.delete_session(session_id)


# ── Query (new rag.service path with legacy fallback) ──────────────

@router.post("/query", response_model=QueryResponse)
async def query(data: QueryRequest):
    await _validate_query(data.kb_id, data.session_id)

    # Try new rag.service first
    try:
        from rag.service import rag_service
        result = await rag_service.query(data.kb_id, data.query)
        history = ChatHistoryService()
        await history.add_message(data.session_id, "user", data.query)
        await history.add_message(data.session_id, "assistant",
                                   result["answer"], result["sources"])
        return result
    except Exception as exc:
        logger.warning("rag.service query failed: %s; falling back to legacy", exc)

    # Legacy fallback
    from app.services.rag_service import RAGService
    legacy = RAGService()
    return await legacy.query(data.kb_id, data.session_id, data.query)


@router.post("/query/stream")
async def query_stream(data: QueryRequest):
    await _validate_query(data.kb_id, data.session_id)

    async def event_generator():
        try:
            from rag.service import rag_service
            result = await rag_service.query(data.kb_id, data.query)

            yield f"event: chunk\n"
            yield f"data: {json.dumps({'text': result['answer']}, ensure_ascii=False)}\n\n"
            yield f"event: sources\n"
            yield f"data: {json.dumps({'sources': result['sources']}, ensure_ascii=False)}\n\n"
            yield f"event: done\n"
            yield f"data: {json.dumps({'message_id': 'rag_svc', 'score': result.get('score', 0)}, ensure_ascii=False)}\n\n"
            return
        except Exception as exc:
            logger.warning("rag.service stream failed: %s; falling back to legacy", exc)

        # Legacy fallback
        from app.services.rag_service import RAGService
        legacy = RAGService()
        async for event in legacy.query_stream(data.kb_id, data.session_id, data.query):
            event_type = event["type"]
            payload = {k: v for k, v in event.items() if k != "type"}
            yield f"event: {event_type}\n"
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive",
                 "X-Accel-Buffering": "no"},
    )
