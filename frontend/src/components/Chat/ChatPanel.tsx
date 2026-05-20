import { useState, useEffect, useCallback } from 'react';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { useStreamChat } from '../../hooks/useStreamChat';
import { useAppStore } from '../../store/appStore';
import { createSession, getSession, listSessions } from '../../api/chat';
import type { Message } from '../../types';
import { Plus } from 'lucide-react';

export function ChatPanel() {
  const { activeKnowledgeBaseId, activeSessionId, setActiveSession, setMessages, isStreaming, setChatSessions } = useAppStore();
  const { streamQuery, cancelStream } = useStreamChat();
  const [error, setError] = useState<string | null>(null);

  // Load session history when switching sessions
  useEffect(() => {
    if (!activeSessionId) { setMessages([]); return; }
    (async () => {
      try {
        const data = await getSession(activeSessionId);
        // Parse sources JSON strings from backend
        const messages = (data.messages || []).map((m: Message) => ({
          ...m,
          sources: typeof m.sources === 'string' ? JSON.parse(m.sources) : (m.sources || undefined),
        }));
        // Only set messages if still on the same session and not streaming
        const state = useAppStore.getState();
        if (state.activeSessionId === activeSessionId && !state.isStreaming) {
          setMessages(messages);
        }
      } catch {
        setError('加载对话记录失败');
      }
    })();
  }, [activeSessionId, setMessages]);

  const refreshSessionList = useCallback(async () => {
    if (!activeKnowledgeBaseId) return;
    try {
      const sessions = await listSessions(activeKnowledgeBaseId);
      setChatSessions(sessions);
    } catch { console.error('Failed to refresh session list'); }
  }, [activeKnowledgeBaseId, setChatSessions]);

  const handleSend = async (query: string) => {
    if (!activeKnowledgeBaseId) return;
    setError(null);

    let sessionId = activeSessionId;
    if (!sessionId) {
      try {
        const session = await createSession(activeKnowledgeBaseId, '新对话');
        sessionId = session.id;
        setActiveSession(session.id);
        refreshSessionList();
      } catch {
        setError('创建会话失败');
        return;
      }
    }

    // Add user message to UI immediately
    const { addMessage } = useAppStore.getState();
    addMessage({
      id: `user_${Date.now()}`,
      role: 'user',
      content: query,
      created_at: new Date().toISOString(),
    });

    try {
      await streamQuery(activeKnowledgeBaseId, sessionId, query);
      refreshSessionList();
    } catch {
      setError('查询失败');
    }
  };

  const handleNewChat = async () => {
    if (!activeKnowledgeBaseId) return;
    try {
      const session = await createSession(activeKnowledgeBaseId, '新对话');
      setActiveSession(session.id);
      refreshSessionList();
    } catch {
      setError('创建会话失败');
    }
  };

  if (!activeKnowledgeBaseId) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="text-center text-gray-400">
          <h1 className="text-2xl font-semibold text-gray-600 mb-2">RAG 知识库系统</h1>
          <p>从左侧选择一个知识库开始提问</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-white">
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <span className="text-sm text-gray-500">
          {activeSessionId ? '对话中' : '新对话'}
        </span>
        <button
          onClick={handleNewChat}
          title="新建会话"
          className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 px-2 py-1 rounded hover:bg-blue-50 transition-colors"
        >
          <Plus className="w-3.5 h-3.5" /> 新对话
        </button>
      </div>
      {error && (
        <div className="mx-4 mt-2 p-2 bg-red-50 text-red-600 text-sm rounded-lg">
          {error}
          <button className="ml-2 underline" onClick={() => setError(null)}>关闭</button>
        </div>
      )}
      <MessageList />
      <ChatInput onSend={handleSend} onCancel={cancelStream} isStreaming={isStreaming} />
    </div>
  );
}
