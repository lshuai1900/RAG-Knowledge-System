import { useEffect, useState, useCallback } from 'react';
import { Book, Plus, Trash2, Loader2 } from 'lucide-react';
import { listKnowledgeBases, deleteKnowledgeBase } from '../../api/knowledgeBase';
import { useAppStore } from '../../store/appStore';
interface Props {
  onShowForm: () => void;
}

export function KnowledgeBaseList({ onShowForm }: Props) {
  const { knowledgeBases, setKnowledgeBases, activeKnowledgeBaseId, setActiveKnowledgeBase } = useAppStore();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchKBs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listKnowledgeBases();
      setKnowledgeBases(data);
    } catch {
      setError('加载知识库失败');
    } finally {
      setLoading(false);
    }
  }, [setKnowledgeBases]);

  // eslint-disable-next-line react-hooks/set-state-in-effect -- zustand store sync
  useEffect(() => { fetchKBs(); }, [fetchKBs]);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('确定删除此知识库及所有文档？')) return;
    try {
      await deleteKnowledgeBase(id);
      if (activeKnowledgeBaseId === id) setActiveKnowledgeBase(null);
      fetchKBs();
    } catch {
      alert('删除失败');
    }
  };

  if (loading) return <div className="flex items-center gap-2 text-sm text-gray-400 p-2"><Loader2 className="w-4 h-4 animate-spin" /> 加载中...</div>;
  if (error) return <div className="text-sm text-red-500 p-2">{error}<button className="ml-2 underline text-blue-500" onClick={fetchKBs}>重试</button></div>;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between px-2 mb-2">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">知识库</span>
        <button onClick={onShowForm} className="p-1 hover:bg-gray-100 rounded text-gray-400 hover:text-gray-600" title="新建知识库">
          <Plus className="w-4 h-4" />
        </button>
      </div>
      {knowledgeBases.length === 0 ? (
        <p className="text-sm text-gray-400 px-2">暂无知识库，点击 + 创建一个</p>
      ) : (
        knowledgeBases.map((kb) => (
          <button
            key={kb.id}
            onClick={() => setActiveKnowledgeBase(kb.id)}
            className={`w-full text-left px-3 py-2 rounded-lg flex items-center gap-3 transition-colors ${
              activeKnowledgeBaseId === kb.id ? 'bg-blue-50 text-blue-700' : 'hover:bg-gray-100 text-gray-700'
            }`}
          >
            <Book className="w-4 h-4 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium truncate">{kb.name}</div>
              <div className="text-xs text-gray-400">{kb.document_count ?? 0} 篇文档</div>
            </div>
            <Trash2 className="w-3.5 h-3.5 text-gray-300 hover:text-red-500 flex-shrink-0" onClick={(e) => handleDelete(kb.id, e)} />
          </button>
        ))
      )}
    </div>
  );
}
