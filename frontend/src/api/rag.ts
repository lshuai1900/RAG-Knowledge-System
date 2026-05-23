import apiClient from './client';
import type { RagStatus } from '../types';

export async function getRagStatus(): Promise<RagStatus> {
  const res = await apiClient.get('/rag/status');
  return res.data;
}
