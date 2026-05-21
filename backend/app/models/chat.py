from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    kb_id: str | None = None
    title: str = "New Chat"


class SessionResponse(BaseModel):
    id: str
    kb_id: str | None = None
    title: str
    message_count: int = 0
    created_at: str
    updated_at: str


class SessionDetailResponse(BaseModel):
    session: SessionResponse
    messages: list[dict]


class QueryRequest(BaseModel):
    kb_id: str
    session_id: str
    query: str = Field(..., min_length=1)


class QueryResponse(BaseModel):
    model_config = {"extra": "allow"}

    answer: str
    sources: list[dict]
    message_id: str = ""
    confidence: str | None = None
    reason: str | None = None
    top_similarity_score: float | None = None
    threshold: float | None = None
