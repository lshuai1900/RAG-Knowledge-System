import { useEffect, useState, useCallback, useRef } from 'react';
import { Trash2, FileText, Loader2, AlertCircle, CheckCircle2, Clock } from 'lucide-react';
import { listDocuments, deleteDocument } from '../../api/document';
import { useAppStore } from '../../store/appStore';
import { ConfirmModal } from '../shared/ConfirmModal';
import { EmptyState } from '../shared/EmptyState';
import { StatusPill } from '../shared/StatusPill';
import { toast } from '../shared/toast';

function statusMeta(status: string) {
  switch (status) {
    case 'pending': return { icon: Clock, variant: 'neutral' as const, label: '等待中' };
    case 'processing': return { icon: Loader2, variant: 'info' as const, label: '解析中', spin: true };
    case 'ready': return { icon: CheckCircle2, variant: 'success' as const, label: '就绪' };
    case 'failed': return { icon: AlertCircle, variant: 'error' as const, label: '失败' };
    default: return { icon: FileText, variant: 'neutral' as const, label: status };
  }
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocumentList() {
  const { activeKnowledgeBaseId, documents, setDocuments } = useAppStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchDocs = useCallback(async () => {
    if (!activeKnowledgeBaseId) { setDocuments([]); return; }
    setLoading(true);
    setError(null);
    try {
      const data = await listDocuments(activeKnowledgeBaseId);
      setDocuments(data);
    } catch {
      setError('加载文档列表失败');
    } finally {
      setLoading(false);
    }
  }, [activeKnowledgeBaseId, setDocuments]);

  // eslint-disable-next-line react-hooks/set-state-in-effect -- zustand store sync
  useEffect(() => { fetchDocs(); }, [fetchDocs]);

  useEffect(() => {
    const handler = () => fetchDocs();
    window.addEventListener('documents-changed', handler);
    return () => window.removeEventListener('documents-changed', handler);
  }, [fetchDocs]);

  useEffect(() => {
    const hasProcessing = documents.some(
      (d) => d.status === 'pending' || d.status === 'processing'
    );
    if (hasProcessing && !pollRef.current) {
      pollRef.current = setInterval(fetchDocs, 1500);
    } else if (!hasProcessing && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    };
  }, [documents, fetchDocs]);

  const handleDeleteConfirm = async () => {
    if (!activeKnowledgeBaseId || !deleteTarget) return;
    setDeleting(true);
    try {
      const result = await deleteDocument(activeKnowledgeBaseId, deleteTarget);
      if (result.warnings.length > 0) {
        result.warnings.forEach((w) => toast('warning', w));
      }
      toast('success', '文档已删除');
      setDeleteTarget(null);
      fetchDocs();
    } catch {
      toast('error', '删除文档失败');
    } finally {
      setDeleting(false);
    }
  };

  if (!activeKnowledgeBaseId) return null;

  if (loading && documents.length === 0) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex items-center gap-3 p-3">
            <div className="skeleton h-8 w-8 rounded-lg" />
            <div className="flex-1 space-y-2">
              <div className="skeleton h-3 w-3/4" />
              <div className="skeleton h-2 w-1/2" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-500 text-sm">{error}</p>
        <button onClick={fetchDocs} className="mt-2 text-sm text-brand-600 hover:underline">重试</button>
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <EmptyState
        icon={<FileText className="h-6 w-6" />}
        title="暂无文档"
        description="上传 PDF、TXT、MD 或 DOCX 文件开始构建知识索引"
      />
    );
  }

  return (
    <>
      <ConfirmModal
        open={deleteTarget !== null}
        title="删除文档"
        message="确定删除此文档？删除将同步清理向量索引和 BM25 索引。"
        confirmLabel="确认删除"
        danger
        loading={deleting}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteTarget(null)}
      />
      <div className="space-y-1.5">
        {documents.map((doc) => {
          const meta = statusMeta(doc.status);
          return (
            <div
              key={doc.id}
              className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-surface-50 group transition-colors"
            >
              <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-surface-100 text-text-tertiary">
                <FileText className="h-4 w-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-text-primary truncate font-medium">{doc.filename}</span>
                  <StatusPill label={meta.label} variant={meta.variant} />
                </div>
                <div className="flex items-center gap-2 mt-0.5 text-xs text-text-tertiary">
                  <span>{formatSize(doc.file_size ?? 0)}</span>
                  {doc.chunk_count > 0 && (
                    <span>{doc.chunk_count} 个文本块</span>
                  )}
                </div>
              </div>
              <button
                onClick={() => setDeleteTarget(doc.id)}
                className="p-1.5 rounded-lg text-text-tertiary hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all"
                aria-label={`删除 ${doc.filename}`}
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          );
        })}
      </div>
    </>
  );
}
