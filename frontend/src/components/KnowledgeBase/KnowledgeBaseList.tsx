import { useEffect, useState, useCallback } from 'react';
import { Book, Plus, Trash2, FileText, Calendar } from 'lucide-react';
import { listKnowledgeBases, deleteKnowledgeBase } from '../../api/knowledgeBase';
import { useAppStore } from '../../store/appStore';
import { ConfirmModal } from '../shared/ConfirmModal';
import { EmptyState } from '../shared/EmptyState';
import { Card } from '../shared/Card';
import { Badge } from '../shared/Badge';
import { toast } from '../shared/toast';

interface Props {
  onShowForm: () => void;
}

function formatDate(iso: string) {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
  } catch {
    return iso;
  }
}

export function KnowledgeBaseList({ onShowForm }: Props) {
  const { knowledgeBases, setKnowledgeBases, activeKnowledgeBaseId, setActiveKnowledgeBase } = useAppStore();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

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

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      const result = await deleteKnowledgeBase(deleteTarget);
      if (result.warnings.length > 0) {
        result.warnings.forEach((w) => toast('warning', w));
      }
      toast('success', '知识库已删除');
      if (activeKnowledgeBaseId === deleteTarget) setActiveKnowledgeBase(null);
      setDeleteTarget(null);
      fetchKBs();
    } catch {
      toast('error', '删除知识库失败');
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="rounded-xl border border-surface-200 bg-white p-5 space-y-3">
            <div className="skeleton h-5 w-2/3" />
            <div className="skeleton h-3 w-full" />
            <div className="skeleton h-3 w-1/2" />
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500 text-sm">{error}</p>
        <button
          onClick={fetchKBs}
          className="mt-2 text-sm text-brand-600 hover:underline"
        >
          重试
        </button>
      </div>
    );
  }

  if (knowledgeBases.length === 0) {
    return (
      <>
        <EmptyState
          title="创建第一个知识库"
          description="创建知识库后即可上传文档、构建索引并开始智能问答"
          action={
            <button
              onClick={onShowForm}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-lg hover:bg-brand-700 transition-colors"
            >
              <Plus className="h-4 w-4" />
              新建知识库
            </button>
          }
        />
      </>
    );
  }

  return (
    <>
      <ConfirmModal
        open={deleteTarget !== null}
        title="删除知识库"
        message="确定删除此知识库？\n\n删除知识库将同时删除：\n• 所有文档及上传文件\n• Milvus 向量索引\n• BM25 索引\n• 相关会话记录\n\n此操作不可撤销。"
        confirmLabel="确认删除"
        danger
        loading={deleting}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteTarget(null)}
      />
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {knowledgeBases.map((kb) => (
          <Card
            key={kb.id}
            hover
            onClick={() => setActiveKnowledgeBase(kb.id)}
            className={activeKnowledgeBaseId === kb.id ? 'ring-2 ring-brand-500/30 border-brand-300' : ''}
          >
            <div className="flex items-start gap-4">
              <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
                <Book className="h-5 w-5" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-semibold text-text-primary truncate">{kb.name}</h3>
                  {activeKnowledgeBaseId === kb.id && (
                    <Badge variant="brand">当前</Badge>
                  )}
                </div>
                {kb.description && (
                  <p className="text-xs text-text-tertiary mt-0.5 line-clamp-2">{kb.description}</p>
                )}
                <div className="flex items-center gap-3 mt-3 text-xs text-text-tertiary">
                  <span className="inline-flex items-center gap-1">
                    <FileText className="h-3 w-3" />
                    {kb.document_count ?? 0} 篇文档
                  </span>
                  {kb.chunk_count != null && (
                    <span>{kb.chunk_count} 块</span>
                  )}
                  {kb.created_at && (
                    <span className="inline-flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {formatDate(kb.created_at)}
                    </span>
                  )}
                </div>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); setDeleteTarget(kb.id); }}
                className="flex-shrink-0 p-1.5 rounded-lg text-text-tertiary hover:text-red-500 hover:bg-red-50 transition-colors"
                aria-label={`删除知识库 ${kb.name}`}
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </Card>
        ))}
      </div>
    </>
  );
}
