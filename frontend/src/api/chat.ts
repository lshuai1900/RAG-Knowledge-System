import apiClient from './client';
import type { ChatSession, Message } from '../types';

export async function createSession(kbId: string, title?: string): Promise<ChatSession> {
  const res = await apiClient.post('/chat/sessions', { kb_id: kbId, title });
  return res.data;
}

export async function listSessions(kbId?: string): Promise<ChatSession[]> {
  const params = kbId ? `?kb_id=${kbId}` : '';
  const res = await apiClient.get(`/chat/sessions${params}`);
  return res.data;
}

export async function getSession(sessionId: string): Promise<{ session: ChatSession; messages: Message[] }> {
  const res = await apiClient.get(`/chat/sessions/${sessionId}`);
  return res.data;
}

export async function deleteSession(sessionId: string): Promise<void> {
  await apiClient.delete(`/chat/sessions/${sessionId}`);
}
