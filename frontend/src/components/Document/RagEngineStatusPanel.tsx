import { useEffect, useState } from 'react';
import { CheckCircle2, Cpu, Loader2 } from 'lucide-react';
import { getRagStatus } from '../../api/rag';
import type { RagStatus } from '../../types';

function formatValue(value: string | number | boolean) {
  if (typeof value === 'boolean') {
    return value ? 'true' : 'false';
  }
  return String(value);
}

export function RagEngineStatusPanel() {
  const [data, setData] = useState<RagStatus | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const fetchStatus = async () => {
      setLoading(true);
      try {
        const res = await getRagStatus();
        if (!cancelled) {
          setData(res);
        }
      } catch {
        if (!cancelled) {
          setData(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    fetchStatus();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="px-2 text-xs text-gray-500 space-y-1">
      <div className="flex items-center gap-1 text-gray-400">
        <Cpu className="w-3 h-3" />
        <span className="font-medium uppercase tracking-wide">RAG 引擎状态</span>
        {loading && <Loader2 className="w-3 h-3 animate-spin ml-1" />}
      </div>
      {data ? (
        <div className="space-y-1">
          {data.RAG_ENGINE.toLowerCase() === 'rag_lab' && (
            <div className="flex items-center gap-1 text-green-600">
              <CheckCircle2 className="w-3 h-3" />
              <span>rag_lab 已接入</span>
            </div>
          )}
          <div className="grid grid-cols-[auto,1fr] gap-x-3 gap-y-0.5">
            <span>RAG_ENGINE</span>
            <span className="truncate text-gray-700" title={data.RAG_ENGINE}>{data.RAG_ENGINE}</span>

            <span>CHUNK_STRATEGY</span>
            <span className="truncate text-gray-700" title={data.CHUNK_STRATEGY}>{data.CHUNK_STRATEGY}</span>

            <span>RAG_RETRIEVAL_MODE</span>
            <span className="truncate text-gray-700" title={data.RAG_RETRIEVAL_MODE}>{data.RAG_RETRIEVAL_MODE}</span>

            <span>RAG_HYBRID_FUSION</span>
            <span className="truncate text-gray-700" title={data.RAG_HYBRID_FUSION}>{data.RAG_HYBRID_FUSION}</span>

            <span>RAG_USE_RERANK</span>
            <span className="truncate text-gray-700">{formatValue(data.RAG_USE_RERANK)}</span>

            <span>RAG_RERANK_TOP_N</span>
            <span className="truncate text-gray-700">{formatValue(data.RAG_RERANK_TOP_N)}</span>
          </div>
        </div>
      ) : !loading ? (
        <span className="text-gray-400">无法获取</span>
      ) : null}
    </div>
  );
}
