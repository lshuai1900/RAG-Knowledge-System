export interface RagStatus {
  RAG_ENGINE: string;
  CHUNK_STRATEGY: string;
  RAG_RETRIEVAL_MODE: string;
  RAG_HYBRID_FUSION: string;
  RAG_USE_RERANK: boolean;
  RAG_RERANK_TOP_N: number;
}
