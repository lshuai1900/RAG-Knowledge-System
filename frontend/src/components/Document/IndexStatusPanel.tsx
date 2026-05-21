import { useEffect, useState, useCallback } from 'react';
import { Loader2, HardDrive, FileText, Database } from 'lucide-react';
import { getIndexStatus } from '../../api/knowledgeBase';
import { useAppStore } from '../../store/appStore';
import type { IndexStatusResponse } from '../../types';

export function IndexStatusPanel() {
  const { activeKnowledgeBaseId, documents } = useAppStore();
  const [data, setData] = useState<IndexStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchStatus = useCallback(async () => {
    if (!activeKnowledgeBaseId) { setData(null); return; }
    setLoading(true);
    try {
      const res = await getIndexStatus(activeKnowledgeBaseId);
      setData(res);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [activeKnowledgeBaseId]);

  // eslint-disable-next-line react-hooks/set-state-in-effect -- async status fetch after knowledge base changes
  useEffect(() => { fetchStatus(); }, [fetchStatus]);

  // eslint-disable-next-line react-hooks/set-state-in-effect -- async status fetch after document changes
  useEffect(() => { fetchStatus(); }, [documents, fetchStatus]);

  if (!activeKnowledgeBaseId) return null;

  return (
    <div className="px-2 text-xs text-gray-500 space-y-1">
      <div className="flex items-center gap-1 text-gray-400">
        <HardDrive className="w-3 h-3" />
        <span className="font-medium uppercase tracking-wide">索引状态</span>
        {loading && <Loader2 className="w-3 h-3 animate-spin ml-1" />}
      </div>
      {data ? (
        <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
          <span className="flex items-center gap-1">
            <FileText className="w-3 h-3" /> 文档
          </span>
          <span>{data.document_count} 篇</span>

          <span className="flex items-center gap-1">
            <Database className="w-3 h-3" /> 向量块
          </span>
          <span>{data.chunk_count}</span>

          <span>BM25 索引</span>
          <span>
            {data.bm25_index_exists
              ? `✓ ${data.bm25_chunk_count}`
              : '—'}
          </span>

          {Object.keys(data.documents_by_status).length > 0 && (
            <>
              <span className="col-span-2 mt-1 text-gray-400">文档状态</span>
              {Object.entries(data.documents_by_status).map(([status, count]) => (
                <span key={status} className="col-span-2 flex justify-between">
                  <span>{status}</span>
                  <span>{count}</span>
                </span>
              ))}
            </>
          )}
        </div>
      ) : !loading ? (
        <span className="text-gray-400">无法获取</span>
      ) : null}
    </div>
  );
}
