import { useEffect, useState } from 'react';
import type { ViewType } from './AppLayout';
import {
  LayoutDashboard, BookOpen, FileText, MessageSquare,
  Cpu, Brain, Loader2, WifiOff,
} from 'lucide-react';
import { getRagStatus } from '../../api/rag';
import type { RagStatus } from '../../types';

const navItems: { id: ViewType; label: string; icon: typeof LayoutDashboard }[] = [
  { id: 'dashboard', label: '总览', icon: LayoutDashboard },
  { id: 'knowledge-bases', label: '知识库', icon: BookOpen },
  { id: 'documents', label: '文档管理', icon: FileText },
  { id: 'chat', label: '智能问答', icon: MessageSquare },
  { id: 'rag-status', label: 'RAG 引擎', icon: Cpu },
];

interface Props {
  currentView: ViewType;
  onNavigate: (view: ViewType) => void;
}

export function Sidebar({ currentView, onNavigate }: Props) {
  const [status, setStatus] = useState<RagStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    setError(false);
    getRagStatus()
      .then((s) => { if (!cancelled) { setStatus(s); setLoading(false); } })
      .catch(() => { if (!cancelled) { setError(true); setLoading(false); } });
    return () => { cancelled = true; };
  }, []);

  const provider = status?.embedding_provider || '—';
  const retrieval = status?.retrieval_mode || status?.RAG_RETRIEVAL_MODE || '—';
  const indexReady = status?.index_ready ?? false;
  const statusLine = error
    ? 'backend offline'
    : loading
      ? 'loading...'
      : `${provider} · ${retrieval} · ${indexReady ? 'indexed' : 'no index'}`;

  const iconColor = error ? 'bg-red-100 text-red-600'
    : indexReady ? 'bg-emerald-100 text-emerald-600'
    : 'bg-amber-100 text-amber-600';

  return (
    <aside className="flex h-full w-64 flex-col bg-white border-r border-surface-200">
      {/* Brand */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-surface-100">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white shadow-sm">
          <Brain className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <div className="text-sm font-semibold text-text-primary leading-tight">
            RAG Knowledge
          </div>
          <div className="text-[11px] text-text-tertiary leading-tight">
            System
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentView === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                isActive
                  ? 'bg-brand-50 text-brand-700 shadow-sm'
                  : 'text-text-secondary hover:bg-surface-50 hover:text-text-primary'
              }`}
            >
              <Icon className={`h-4 w-4 flex-shrink-0 ${isActive ? 'text-brand-600' : 'text-text-tertiary'}`} />
              {item.label}
            </button>
          );
        })}
      </nav>

      {/* Footer status — real data from RAG status API */}
      <div className="px-3 py-4 border-t border-surface-100 space-y-2">
        <div className={`flex items-center gap-2 px-2 py-2 rounded-lg bg-surface-50`}>
          <div className={`flex h-7 w-7 items-center justify-center rounded-lg ${iconColor}`}>
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
              : error ? <WifiOff className="h-3.5 w-3.5" />
              : <Cpu className="h-3.5 w-3.5" />}
          </div>
          <div className="min-w-0">
            <div className="text-[11px] font-medium text-text-primary">RAG Engine</div>
            <div className="text-[10px] text-text-tertiary truncate" title={statusLine}>
              {statusLine}
            </div>
          </div>
        </div>
        <p className="text-[10px] text-text-tertiary text-center">
          RAG Knowledge System v1.0
        </p>
      </div>
    </aside>
  );
}
