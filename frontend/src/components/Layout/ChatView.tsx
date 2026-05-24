import { useState, useEffect, useCallback } from 'react';
import { MessageList } from '../Chat/MessageList';
import { ChatInput } from '../Chat/ChatInput';
import { ChatSessionList } from '../Chat/ChatSessionList';
import { useStreamChat } from '../../hooks/useStreamChat';
import { useAppStore } from '../../store/appStore';
import { createSession, getSession, listSessions } from '../../api/chat';
import { EmptyState } from '../shared/EmptyState';
import type { Message } from '../../types';
import type { ViewType } from './AppLayout';
import { Plus, MessageSquare, BookOpen, Lightbulb, Search, FileSearch } from 'lucide-react';

const EXAMPLE_QUESTIONS = [
  { icon: Lightbulb, text: '总结这篇论文的研究方法' },
  { icon: FileSearch, text: '列出文档中的关键结论' },
  { icon: Search, text: '这篇文章的创新点是什么？' },
  { icon: MessageSquare, text: '请根据知识库回答并给出引用' },
];

interface ChatViewProps {
  onNavigate?: (view: ViewType) => void;
}

export function ChatView({ onNavigate }: ChatViewProps) {
  const { activeKnowledgeBaseId, activeSessionId, setActiveSession, setMessages, isStreaming, setChatSessions, knowledgeBases, setActiveKnowledgeBase } = useAppStore();
  const { streamQuery, cancelStream } = useStreamChat();
  const [error, setError] = useState<string | null>(null);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const messages = useAppStore((s) => s.messages);

  useEffect(() => {
    if (!activeSessionId) { setMessages([]); return; }
    (async () => {
      try {
        const data = await getSession(activeSessionId);
        const msgs = (data.messages || []).map((m: Message) => ({
          ...m,
          sources: typeof m.sources === 'string' ? JSON.parse(m.sources) : (m.sources || undefined),
        }));
        const state = useAppStore.getState();
        if (state.activeSessionId === activeSessionId && !state.isStreaming) {
          setMessages(msgs);
        }
      } catch {
        setError('加载对话记录失败');
      }
    })();
  }, [activeSessionId, setMessages]);

  const refreshSessionList = useCallback(async () => {
    if (!activeKnowledgeBaseId) return;
    setSessionsLoading(true);
    try {
      const sessions = await listSessions(activeKnowledgeBaseId);
      setChatSessions(sessions);
    } catch { /* ignore */ }
    finally { setSessionsLoading(false); }
  }, [activeKnowledgeBaseId, setChatSessions]);

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (!activeKnowledgeBaseId) return;
    refreshSessionList();
  }, [activeKnowledgeBaseId, refreshSessionList]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const handleSend = async (query: string) => {
    if (!activeKnowledgeBaseId) return;
    setError(null);

    let sessionId = activeSessionId;
    if (!sessionId) {
      try {
        const session = await createSession(activeKnowledgeBaseId, query.slice(0, 30));
        sessionId = session.id;
        setActiveSession(session.id);
        refreshSessionList();
      } catch {
        setError('创建会话失败');
        return;
      }
    }

    const { addMessage } = useAppStore.getState();
    // eslint-disable-next-line react-hooks/purity -- event handler
    const msgId = `user_${Date.now()}`;
    addMessage({
      id: msgId,
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

  // No KB selected state
  if (!activeKnowledgeBaseId) {
    return (
      <div className="h-full overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 py-8">
          <EmptyState
            icon={<BookOpen className="h-8 w-8" />}
            title="请先选择一个知识库"
            description="选择知识库后即可开始智能问答对话"
            action={
              <div className="flex flex-col items-center gap-3">
                <div className="flex flex-wrap gap-2 justify-center">
                  {knowledgeBases.map((kb) => (
                    <button
                      key={kb.id}
                      onClick={() => setActiveKnowledgeBase(kb.id)}
                      className="px-4 py-2 text-sm font-medium text-brand-700 bg-brand-50 rounded-lg hover:bg-brand-100 transition-colors"
                    >
                      {kb.name}
                    </button>
                  ))}
                </div>
                {knowledgeBases.length === 0 && onNavigate && (
                  <button
                    onClick={() => onNavigate('knowledge-bases')}
                    className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-lg hover:bg-brand-700 transition-colors"
                  >
                    <Plus className="h-4 w-4" />
                    新建知识库
                  </button>
                )}
              </div>
            }
          />
        </div>
      </div>
    );
  }

  const activeKB = knowledgeBases.find((kb) => kb.id === activeKnowledgeBaseId);

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Chat header */}
      <div className="flex-shrink-0 px-5 py-3 border-b border-surface-100 flex items-center justify-between">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
            <MessageSquare className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-text-primary truncate">
              {activeKB?.name ?? '知识库问答'}
            </h2>
            <p className="text-xs text-text-tertiary">
              {activeSessionId ? '对话中' : '新对话'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <ChatSessionList
            compact
            sessionsLoading={sessionsLoading}
          />
          <button
            onClick={handleNewChat}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-brand-600 hover:bg-brand-50 rounded-lg transition-colors"
          >
            <Plus className="h-3.5 w-3.5" />
            新对话
          </button>
        </div>
      </div>

      {error && (
        <div className="flex-shrink-0 mx-5 mt-2 p-2.5 bg-red-50 text-red-600 text-sm rounded-lg flex items-center justify-between">
          <span>{error}</span>
          <button className="text-xs underline" onClick={() => setError(null)}>关闭</button>
        </div>
      )}

      {/* Messages or empty state */}
      {messages.length === 0 ? (
        <div className="flex-1 overflow-y-auto">
          <div className="flex flex-col items-center justify-center min-h-full px-6 py-12">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50 text-brand-500 mb-5">
              <MessageSquare className="h-8 w-8" />
            </div>
            <h3 className="text-lg font-semibold text-text-primary mb-2">
              开始智能问答
            </h3>
            <p className="text-sm text-text-tertiary mb-8 max-w-md text-center">
              基于知识库文档进行检索增强生成，每个回答都会标注引用来源
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
              {EXAMPLE_QUESTIONS.map((q) => (
                <button
                  key={q.text}
                  onClick={() => handleSend(q.text)}
                  className="flex items-center gap-2 px-4 py-3 text-left text-sm text-text-secondary bg-surface-50 border border-surface-200 rounded-xl hover:bg-brand-50 hover:border-brand-200 hover:text-brand-700 transition-all"
                  disabled={isStreaming}
                >
                  <q.icon className="h-4 w-4 flex-shrink-0 text-text-tertiary" />
                  {q.text}
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <MessageList />
      )}

      <ChatInput onSend={handleSend} onCancel={cancelStream} isStreaming={isStreaming} />
    </div>
  );
}
