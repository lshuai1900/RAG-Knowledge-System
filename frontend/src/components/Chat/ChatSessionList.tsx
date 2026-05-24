import { useState } from 'react';
import { MessageSquare, Trash2, Loader2 } from 'lucide-react';
import { deleteSession } from '../../api/chat';
import { useAppStore } from '../../store/appStore';

interface Props {
  compact?: boolean;
  sessionsLoading?: boolean;
}

export function ChatSessionList({ compact = false, sessionsLoading = false }: Props) {
  const { activeSessionId, setActiveSession, chatSessions, setChatSessions } = useAppStore();
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const handleDelete = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('确定删除此对话？')) return;
    try {
      await deleteSession(sessionId);
      if (activeSessionId === sessionId) setActiveSession(null);
      setChatSessions(chatSessions.filter((s) => s.id !== sessionId));
    } catch { /* ignore */ }
  };

  const handleSelectSession = (sessionId: string) => {
    setActiveSession(sessionId);
    setDropdownOpen(false);
  };

  if (compact) {
    const isVisible = dropdownOpen;

    return (
      <div className="relative">
        <button
          onClick={() => setDropdownOpen(!dropdownOpen)}
          className="text-xs text-text-tertiary hover:text-text-secondary transition-colors px-2 py-1 rounded-lg hover:bg-surface-50"
        >
          {chatSessions.length > 0 ? `${chatSessions.length} 个会话` : '会话'}
        </button>
        {isVisible && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setDropdownOpen(false)} />
            <div className="absolute right-0 top-full mt-1 w-64 bg-white rounded-xl border border-surface-200 shadow-elevated p-1 z-50 max-h-64 overflow-y-auto animate-fade-in">
          {sessionsLoading ? (
            <div className="flex items-center gap-2 px-3 py-2 text-xs text-text-tertiary">
              <Loader2 className="h-3 w-3 animate-spin" /> 加载中...
            </div>
          ) : chatSessions.length === 0 ? (
            <p className="text-xs text-text-tertiary px-3 py-2">暂无对话</p>
          ) : (
            chatSessions.map((s) => (
              <div
                key={s.id}
                onClick={() => handleSelectSession(s.id)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                  s.id === activeSessionId
                    ? 'bg-brand-50 text-brand-700'
                    : 'hover:bg-surface-50 text-text-secondary'
                }`}
              >
                <MessageSquare className="h-3.5 w-3.5 flex-shrink-0" />
                <span className="text-xs flex-1 truncate">{s.title || '新对话'}</span>
                <span className="text-[10px] text-text-tertiary">{s.message_count}</span>
                <Trash2
                  className="h-3 w-3 text-text-tertiary hover:text-red-500 flex-shrink-0"
                  onClick={(e) => handleDelete(s.id, e)}
                />
              </div>
            ))
          )}
        </div>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-0.5">
      <div className="flex items-center justify-between px-2 mb-1">
        <span className="text-xs font-medium text-text-tertiary uppercase tracking-wide">历史对话</span>
        {sessionsLoading && <Loader2 className="h-3 w-3 animate-spin text-text-tertiary" />}
      </div>
      {chatSessions.length === 0 ? (
        <p className="text-xs text-text-tertiary px-2">暂无对话</p>
      ) : (
        chatSessions.map((s) => (
          <div
            key={s.id}
            onClick={() => setActiveSession(s.id)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer group/item transition-colors ${
              s.id === activeSessionId
                ? 'bg-brand-50 text-brand-700'
                : 'hover:bg-surface-50 text-text-secondary'
            }`}
          >
            <MessageSquare className="h-3.5 w-3.5 flex-shrink-0" />
            <span className="text-xs flex-1 truncate">{s.title || '新对话'}</span>
            <span className="text-[10px] text-text-tertiary">{s.message_count}</span>
            <Trash2
              className="h-3 w-3 text-text-tertiary hover:text-red-500 flex-shrink-0 opacity-0 group-hover/item:opacity-100 transition-opacity"
              onClick={(e) => handleDelete(s.id, e)}
            />
          </div>
        ))
      )}
    </div>
  );
}
