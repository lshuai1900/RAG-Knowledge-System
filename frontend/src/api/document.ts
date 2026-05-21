import apiClient from './client';
import type { Document, DeleteDocumentResponse } from '../types';

export async function uploadDocuments(kbId: string, files: File[]): Promise<Document[]> {
  const formData = new FormData();
  files.forEach((f) => formData.append('files', f));
  const res = await apiClient.post(`/knowledge-bases/${kbId}/documents/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

export async function listDocuments(kbId: string): Promise<Document[]> {
  const res = await apiClient.get(`/knowledge-bases/${kbId}/documents`);
  return res.data;
}

export async function getDocumentStatus(kbId: string, docId: string): Promise<{ status: string; chunk_count: number }> {
  const res = await apiClient.get(`/knowledge-bases/${kbId}/documents/${docId}/status`);
  return res.data;
}

export async function deleteDocument(kbId: string, docId: string): Promise<DeleteDocumentResponse> {
  const res = await apiClient.delete(`/knowledge-bases/${kbId}/documents/${docId}`);
  return res.data;
}
