from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    kb_id: str
    filename: str
    file_type: str
    file_size: int
    status: str
    error_message: str | None = None
    chunk_count: int = 0
    created_at: str


class DocumentStatusResponse(BaseModel):
    status: str
    chunk_count: int
    error_message: str | None = None
