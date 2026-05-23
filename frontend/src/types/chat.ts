export interface ChatSession {
  id: string;
  kb_id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  created_at: string;
}

export interface Source {
  content: string;
  document_name: string;
  chunk_index: number;
  score: number;
  source?: string;
  dense_score?: number;
  sparse_score?: number;
  fusion_score?: number;
  rerank_score?: number;
  chunk_strategy?: string;
  similarity_score?: number;
  vector_score?: number;
  bm25_score?: number;
  bm25_score_norm?: number;
  hybrid_score?: number;
  effective_score?: number;
  metadata?: {
    source?: string;
    chunk_strategy?: string;
    [key: string]: unknown;
  };
}

export interface StreamChunk {
  text: string;
}
