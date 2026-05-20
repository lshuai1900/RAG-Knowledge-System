from pydantic import BaseModel, Field


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None


class KnowledgeBaseResponse(BaseModel):
    id: str
    name: str
    description: str
    document_count: int = 0
    chunk_count: int = 0
    created_at: str
    updated_at: str
