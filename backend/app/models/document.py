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


class DeleteDocumentResponse(BaseModel):
    success: bool
    doc_id: str
    milvus_deleted: bool
    bm25_deleted: bool
    warnings: list[str] = []


class DeleteKnowledgeBaseResponse(BaseModel):
    success: bool
    kb_id: str
    documents_deleted: int
    milvus_deleted: bool
    bm25_deleted: bool
    warnings: list[str] = []


class RebuildIndexResponse(BaseModel):
    status: str  # "completed", "partial", "failed"
    kb_id: str
    document_count: int
    success_documents: int
    failed_documents: list[dict] = []
    chunk_count: int
    bm25_chunk_count: int
    warnings: list[str] = []


class IndexStatusResponse(BaseModel):
    kb_id: str
    document_count: int
    chunk_count: int
    bm25_chunk_count: int
    bm25_index_exists: bool
    documents_by_status: dict[str, int] = {}
