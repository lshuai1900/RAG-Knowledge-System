import { useState, useCallback } from 'react';
import { Sidebar } from './Sidebar';
import { DashboardView } from './DashboardView';
import { KnowledgeBaseView } from './KnowledgeBaseView';
import { DocumentView } from './DocumentView';
import { ChatView } from './ChatView';
import { RagStatusView } from './RagStatusView';

export type ViewType = 'dashboard' | 'knowledge-bases' | 'documents' | 'chat' | 'rag-status';

export function AppLayout() {
  const [currentView, setCurrentView] = useState<ViewType>('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleNavigate = useCallback((view: ViewType) => {
    setCurrentView(view);
    setSidebarOpen(false);
  }, []);

  const renderView = () => {
    switch (currentView) {
      case 'dashboard':
        return <DashboardView onNavigate={handleNavigate} />;
      case 'knowledge-bases':
        return <KnowledgeBaseView />;
      case 'documents':
        return <DocumentView onNavigate={handleNavigate} />;
      case 'chat':
        return <ChatView onNavigate={handleNavigate} />;
      case 'rag-status':
        return <RagStatusView />;
      default:
        return <DashboardView onNavigate={handleNavigate} />;
    }
  };

  return (
    <div className="flex h-screen bg-surface-50 overflow-hidden">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`
        fixed inset-y-0 left-0 z-50 w-64 lg:relative lg:flex
        transform transition-transform duration-200 ease-out
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <Sidebar currentView={currentView} onNavigate={handleNavigate} />
      </div>

      {/* Mobile header */}
      <div className="lg:hidden fixed top-0 inset-x-0 z-30 h-14 bg-white border-b border-surface-200 flex items-center px-4 gap-3">
        <button
          onClick={() => setSidebarOpen(true)}
          className="p-2 -ml-2 rounded-lg hover:bg-surface-100 text-text-secondary"
          aria-label="打开菜单"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M3 5h14M3 10h14M3 15h14" />
          </svg>
        </button>
        <span className="font-semibold text-text-primary text-sm">RAG Knowledge System</span>
      </div>

      {/* Main content */}
      <main className="flex-1 overflow-hidden lg:pt-0 pt-14">
        {renderView()}
      </main>
    </div>
  );
}
