export interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  document_count: number;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

export interface CreateKnowledgeBaseRequest {
  name: string;
  description?: string;
}
