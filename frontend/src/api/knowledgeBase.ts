import apiClient from './client';
import type { KnowledgeBase, CreateKnowledgeBaseRequest, DeleteKnowledgeBaseResponse, RebuildIndexResponse, IndexStatusResponse } from '../types';

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

export async function deleteKnowledgeBase(id: string): Promise<DeleteKnowledgeBaseResponse> {
  const res = await apiClient.delete(`/knowledge-bases/${id}`);
  return res.data;
}

export async function rebuildIndex(kbId: string): Promise<RebuildIndexResponse> {
  const res = await apiClient.post(`/knowledge-bases/${kbId}/rebuild-index`);
  return res.data;
}

export async function getIndexStatus(kbId: string): Promise<IndexStatusResponse> {
  const res = await apiClient.get(`/knowledge-bases/${kbId}/index-status`);
  return res.data;
}
