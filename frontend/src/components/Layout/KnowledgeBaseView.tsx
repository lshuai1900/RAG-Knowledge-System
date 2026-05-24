import { useState, useCallback } from 'react';
import { Plus } from 'lucide-react';
import { KnowledgeBaseList } from '../KnowledgeBase/KnowledgeBaseList';
import { KnowledgeBaseForm } from '../KnowledgeBase/KnowledgeBaseForm';
import { SectionHeader } from '../shared/SectionHeader';

export function KnowledgeBaseView() {
  const [showForm, setShowForm] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleCreated = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-4xl mx-auto px-6 py-8">
        <SectionHeader
          title="知识库管理"
          description="创建和管理知识库，每个知识库可独立配置文档索引与检索策略"
          action={
            <button
              onClick={() => setShowForm(true)}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-lg hover:bg-brand-700 transition-colors shadow-sm"
            >
              <Plus className="h-4 w-4" />
              新建知识库
            </button>
          }
        />
        <KnowledgeBaseList key={refreshKey} onShowForm={() => setShowForm(true)} />
      </div>
      {showForm && (
        <KnowledgeBaseForm
          onClose={() => setShowForm(false)}
          onCreated={handleCreated}
        />
      )}
    </div>
  );
}
