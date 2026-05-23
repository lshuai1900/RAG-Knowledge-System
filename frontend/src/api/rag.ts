import apiClient from './client';
import type { RagStatus } from '../types';

type RawRagStatus = Omit<RagStatus, 'RAG_USE_RERANK' | 'RAG_RERANK_TOP_N'> & {
  RAG_USE_RERANK: boolean | string;
  RAG_RERANK_TOP_N: number | string;
};

function normalizeBoolean(value: boolean | string): boolean {
  if (typeof value === 'boolean') return value;
  return ['1', 'true', 'yes', 'y'].includes(value.trim().toLowerCase());
}

function normalizeNumber(value: number | string): number {
  if (typeof value === 'number') return value;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export async function getRagStatus(): Promise<RagStatus> {
  const res = await apiClient.get<RawRagStatus>('/rag/status');
  return {
    ...res.data,
    RAG_USE_RERANK: normalizeBoolean(res.data.RAG_USE_RERANK),
    RAG_RERANK_TOP_N: normalizeNumber(res.data.RAG_RERANK_TOP_N),
  };
}
