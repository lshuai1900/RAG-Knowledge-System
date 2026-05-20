import { useEffect, useState, useCallback, useRef } from 'react';
import { Trash2, FileText, Loader2, AlertCircle, CheckCircle2, Clock } from 'lucide-react';
import { listDocuments, deleteDocument } from '../../api/document';
import { useAppStore } from '../../store/appStore';

export function DocumentList() {
  const { activeKnowledgeBaseId, documents, setDocuments } = useAppStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchDocs = useCallback(async () => {
    if (!activeKnowledgeBaseId) { setDocuments([]); return; }
    setLoading(true);
    setError(null);
    try {
      const data = await listDocuments(activeKnowledgeBaseId);
      setDocuments(data);
    } catch {
      setError('加载文档失败');
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

  // Auto-poll while any document is pending/processing
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

  const handleDelete = async (docId: string) => {
    if (!activeKnowledgeBaseId || !confirm('确定删除此文档？')) return;
    try {
      await deleteDocument(activeKnowledgeBaseId, docId);
      fetchDocs();
    } catch {
      alert('删除失败');
    }
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case 'pending': return <Clock className="w-3.5 h-3.5 text-gray-400" />;
      case 'processing': return <Loader2 className="w-3.5 h-3.5 text-blue-500 animate-spin" />;
      case 'ready': return <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />;
      case 'failed': return <AlertCircle className="w-3.5 h-3.5 text-red-500" />;
      default: return null;
    }
  };

  if (!activeKnowledgeBaseId) return null;
  if (loading) return <div className="flex items-center gap-2 text-sm text-gray-400 px-2"><Loader2 className="w-4 h-4 animate-spin" /> 加载中...</div>;
  if (error) return <div className="text-sm text-red-500 px-2">{error}</div>;

  return (
    <div className="space-y-1">
      {documents.length === 0 ? (
        <p className="text-sm text-gray-400 px-2">暂无文档</p>
      ) : (
        documents.map((doc) => (
          <div key={doc.id} className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-gray-50 group">
            <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="text-sm text-gray-700 truncate">{doc.filename}</div>
              <div className="flex items-center gap-1">
                {statusIcon(doc.status)}
                <span className="text-xs text-gray-400">
                  {doc.status === 'ready' ? `${doc.chunk_count} 个文本块` : doc.status}
                </span>
              </div>
            </div>
            <Trash2
              className="w-3.5 h-3.5 text-gray-300 hover:text-red-500 cursor-pointer flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
              onClick={() => handleDelete(doc.id)}
            />
          </div>
        ))
      )}
    </div>
  );
}
