export interface RagStatus {
  // Structured fields (from backend/rag/)
  rag_engine: string;
  embedding_provider?: string;
  embedding_model?: string;
  embedding_dim?: number;
  index_embedding_dim?: number;
  chunk_strategy?: string;
  chunk_size?: number;
  chunk_overlap?: number;
  chunk_min_size?: number;
  retrieval_mode?: string;
  hybrid_fusion?: string;
  use_rerank?: boolean;
  rerank_model?: string;
  rerank_top_n?: number;
  llm_model?: string;
  documents_count?: number;
  chunks_count?: number;
  index_ready?: boolean;
  last_index_time?: string | null;
  last_query_time?: string | null;
  last_eval_time?: string | null;
  last_eval_score?: {
    hit_at_k: number | null;
    recall_at_k: number | null;
    mrr: number | null;
    faithfulness: number | null;
  } | null;
  health?: string;
  warnings?: string[];
  // Legacy uppercase fields for backward compatibility
  RAG_ENGINE?: string;
  CHUNK_STRATEGY?: string;
  RAG_RETRIEVAL_MODE?: string;
  RAG_HYBRID_FUSION?: string;
  RAG_USE_RERANK?: boolean;
  RAG_RERANK_TOP_N?: number;
}
