import { useState } from 'react';
import { KnowledgeBaseList } from '../KnowledgeBase/KnowledgeBaseList';
import { KnowledgeBaseForm } from '../KnowledgeBase/KnowledgeBaseForm';
import { DocumentManager } from '../Document/DocumentManager';
import { ChatSessionList } from '../Chat/ChatSessionList';

export function Sidebar() {
  const [showForm, setShowForm] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleCreated = () => {
    setRefreshKey((k) => k + 1);
  };

  return (
    <aside className="w-80 bg-white border-r border-gray-200 flex flex-col">
      <div className="p-4 border-b border-gray-100">
        <h2 className="font-semibold text-gray-800">知识库</h2>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-6">
        <KnowledgeBaseList key={refreshKey} onShowForm={() => setShowForm(true)} />
        <hr className="border-gray-100" />
        <ChatSessionList />
        <hr className="border-gray-100" />
        <DocumentManager />
      </div>
      {showForm && <KnowledgeBaseForm onClose={() => setShowForm(false)} onCreated={handleCreated} />}
    </aside>
  );
}
