import apiClient from './client';
import type { KnowledgeBase, CreateKnowledgeBaseRequest } from '../types';

export async function listKnowledgeBases(): Promise<KnowledgeBase[]> {
  const res = await apiClient.get('/knowledge-bases');
  return res.data;
}

export async function createKnowledgeBase(data: CreateKnowledgeBaseRequest): Promise<KnowledgeBase> {
  const res = await apiClient.post('/knowledge-bases', data);
  return res.data;
}

export async function getKnowledgeBase(id: string): Promise<KnowledgeBase> {
  const res = await apiClient.get(`/knowledge-bases/${id}`);
  return res.data;
}

export async function updateKnowledgeBase(id: string, data: Partial<CreateKnowledgeBaseRequest>): Promise<KnowledgeBase> {
  const res = await apiClient.put(`/knowledge-bases/${id}`, data);
  return res.data;
}

export async function deleteKnowledgeBase(id: string): Promise<void> {
  await apiClient.delete(`/knowledge-bases/${id}`);
}
