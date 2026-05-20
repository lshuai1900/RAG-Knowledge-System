import { useEffect } from 'react';
import { MessageSquare, Trash2, Plus } from 'lucide-react';
import { listSessions, deleteSession, createSession } from '../../api/chat';
import { useAppStore } from '../../store/appStore';

export function ChatSessionList() {
  const { activeKnowledgeBaseId, activeSessionId, setActiveSession, chatSessions, setChatSessions } = useAppStore();

  useEffect(() => {
    if (!activeKnowledgeBaseId) { setChatSessions([]); return; }
    (async () => {
      try {
        const sessions = await listSessions(activeKnowledgeBaseId);
        setChatSessions(sessions);
      } catch { console.error('Failed to list sessions'); }
    })();
  }, [activeKnowledgeBaseId, setChatSessions]);

  const handleDelete = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('确定删除此对话？')) return;
    try {
      await deleteSession(sessionId);
      if (activeSessionId === sessionId) setActiveSession(null);
      setChatSessions(chatSessions.filter((s) => s.id !== sessionId));
    } catch { console.error('Chat session operation failed'); }
  };

  const handleNewSession = async () => {
    if (!activeKnowledgeBaseId) return;
    try {
      const session = await createSession(activeKnowledgeBaseId, '新对话');
      setActiveSession(session.id);
      setChatSessions([session, ...chatSessions]);
    } catch { console.error('Chat session operation failed'); }
  };

  if (!activeKnowledgeBaseId) return null;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between px-2 mb-1">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">对话</span>
        <button
          onClick={handleNewSession}
          title="新建对话"
          className="text-gray-400 hover:text-blue-600 transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </div>
      {chatSessions.length === 0 ? (
        <p className="text-xs text-gray-400 px-2">暂无对话</p>
      ) : (
        chatSessions.map((s) => (
          <div
            key={s.id}
            onClick={() => setActiveSession(s.id)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg cursor-pointer group transition-colors ${
              s.id === activeSessionId
                ? 'bg-blue-50 text-blue-700'
                : 'hover:bg-gray-50 text-gray-700'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5 flex-shrink-0" />
            <span className="text-sm flex-1 truncate">{s.title || '新对话'}</span>
            <span className="text-xs text-gray-400 flex-shrink-0">{s.message_count}</span>
            <Trash2
              className="w-3 h-3 text-gray-300 hover:text-red-500 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
              onClick={(e) => handleDelete(s.id, e)}
            />
          </div>
        ))
      )}
    </div>
  );
}
