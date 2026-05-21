export interface Document {
  id: string;
  kb_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: 'pending' | 'processing' | 'ready' | 'failed';
  error_message?: string;
  chunk_count: number;
  created_at: string;
}

export interface DeleteDocumentResponse {
  success: boolean;
  doc_id: string;
  milvus_deleted: boolean;
  bm25_deleted: boolean;
  warnings: string[];
}

export interface DeleteKnowledgeBaseResponse {
  success: boolean;
  kb_id: string;
  documents_deleted: number;
  milvus_deleted: boolean;
  bm25_deleted: boolean;
  warnings: string[];
}

export interface RebuildIndexResponse {
  status: 'completed' | 'partial' | 'failed';
  kb_id: string;
  document_count: number;
  success_documents: number;
  failed_documents: { doc_id: string; filename: string; error: string }[];
  chunk_count: number;
  bm25_chunk_count: number;
  warnings: string[];
}

export interface IndexStatusResponse {
  kb_id: string;
  document_count: number;
  chunk_count: number;
  bm25_chunk_count: number;
  bm25_index_exists: boolean;
  documents_by_status: Record<string, number>;
}
