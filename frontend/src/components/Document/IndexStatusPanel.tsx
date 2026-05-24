import { useEffect, useState, useCallback } from 'react';
import { Loader2, FileText, Database } from 'lucide-react';
import { getIndexStatus } from '../../api/knowledgeBase';
import { useAppStore } from '../../store/appStore';
import { StatusPill } from '../shared/StatusPill';
import type { IndexStatusResponse } from '../../types';

export function IndexStatusPanel() {
  const { activeKnowledgeBaseId, documents } = useAppStore();
  const [data, setData] = useState<IndexStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const fetchStatus = useCallback(async () => {
    if (!activeKnowledgeBaseId) { setData(null); return; }
    setLoading(true);
    setError(false);
    try {
      const res = await getIndexStatus(activeKnowledgeBaseId);
      setData(res);
    } catch {
      setData(null);
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [activeKnowledgeBaseId]);

  // eslint-disable-next-line react-hooks/set-state-in-effect -- async status fetch after KB changes
  useEffect(() => { fetchStatus(); }, [fetchStatus]);

  // eslint-disable-next-line react-hooks/set-state-in-effect -- async status fetch after document changes
  useEffect(() => { fetchStatus(); }, [documents, fetchStatus]);

  if (!activeKnowledgeBaseId) return null;

  if (loading && !data) {
    return (
      <div className="flex items-center gap-2 text-xs text-text-tertiary py-2">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        加载索引状态...
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="text-xs text-text-tertiary py-2">
        无法获取索引状态
        <button onClick={fetchStatus} className="ml-2 text-brand-600 hover:underline">重试</button>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="text-xs space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-lg bg-surface-50 p-2.5">
          <div className="flex items-center gap-1.5 text-text-tertiary mb-1">
            <FileText className="h-3 w-3" />
            文档总数
          </div>
          <div className="text-base font-semibold text-text-primary tabular-nums">{data.document_count}</div>
        </div>
        <div className="rounded-lg bg-surface-50 p-2.5">
          <div className="flex items-center gap-1.5 text-text-tertiary mb-1">
            <Database className="h-3 w-3" />
            向量块
          </div>
          <div className="text-base font-semibold text-text-primary tabular-nums">{data.chunk_count}</div>
        </div>
      </div>

      <div className="rounded-lg bg-surface-50 p-2.5">
        <div className="flex items-center justify-between">
          <span className="text-text-tertiary">BM25 索引</span>
          <StatusPill
            label={data.bm25_index_exists ? `已构建 · ${data.bm25_chunk_count}` : '未构建'}
            variant={data.bm25_index_exists ? 'success' : 'neutral'}
          />
        </div>
      </div>

      {Object.keys(data.documents_by_status).length > 0 && (
        <div className="space-y-1">
          <span className="text-text-tertiary font-medium">文档状态分布</span>
          {Object.entries(data.documents_by_status).map(([status, count]) => (
            <div key={status} className="flex items-center justify-between">
              <span className="text-text-secondary">{status}</span>
              <span className="font-medium tabular-nums">{count}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
