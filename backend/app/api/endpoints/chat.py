import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.models.chat import SessionCreate, SessionResponse, SessionDetailResponse, QueryRequest, QueryResponse
from app.services.chat_history_service import ChatHistoryService
from app.services.rag_service import RAGService
from app.core.exceptions import NotFoundException

router = APIRouter()


def get_history_service() -> ChatHistoryService:
    return ChatHistoryService()


def get_rag_service() -> RAGService:
    return RAGService()


@router.post("/sessions", response_model=SessionResponse, status_code=201)
async def create_session(data: SessionCreate, service: ChatHistoryService = Depends(get_history_service)):
    return await service.create_session(data.kb_id, data.title)


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(kb_id: str | None = None, service: ChatHistoryService = Depends(get_history_service)):
    return await service.list_sessions(kb_id)


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(session_id: str, service: ChatHistoryService = Depends(get_history_service)):
    session = await service.get_session(session_id)
    if not session:
        raise NotFoundException("Session", session_id)
    messages = await service.get_messages(session_id)
    return {"session": session, "messages": messages}


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str, service: ChatHistoryService = Depends(get_history_service)):
    session = await service.get_session(session_id)
    if not session:
        raise NotFoundException("Session", session_id)
    await service.delete_session(session_id)


@router.post("/query", response_model=QueryResponse)
async def query(data: QueryRequest, rag_service: RAGService = Depends(get_rag_service)):
    return await rag_service.query(data.kb_id, data.session_id, data.query)


@router.post("/query/stream")
async def query_stream(data: QueryRequest, rag_service: RAGService = Depends(get_rag_service)):
    async def event_generator():
        async for event in rag_service.query_stream(data.kb_id, data.session_id, data.query):
            event_type = event["type"]
            payload = {k: v for k, v in event.items() if k != "type"}
            yield f"event: {event_type}\n"
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
