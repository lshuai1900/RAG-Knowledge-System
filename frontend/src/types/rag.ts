export interface RagStatus {
  // New structured fields
  rag_engine: string;
  chunk_strategy: string;
  chunk_size: number;
  chunk_overlap: number;
  retrieval_mode: string;
  hybrid_fusion: string;
  use_rerank: boolean;
  rerank_top_n: number;
  embedding_model: string;
  llm_model: string;
  chunks_count: number;
  index_ready: boolean;
  last_index_time: string | null;
  last_eval_time: string | null;
  last_eval_score: {
    hit_at_k: number | null;
    recall_at_k: number | null;
    mrr: number | null;
    faithfulness: number | null;
  } | null;
  // Legacy uppercase fields for backward compatibility
  RAG_ENGINE: string;
  CHUNK_STRATEGY: string;
  RAG_RETRIEVAL_MODE: string;
  RAG_HYBRID_FUSION: string;
  RAG_USE_RERANK: boolean;
  RAG_RERANK_TOP_N: number;
}
