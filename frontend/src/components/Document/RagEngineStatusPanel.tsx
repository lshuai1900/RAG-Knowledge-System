import { useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  Cpu,
  Database,
  FileUp,
  Loader2,
  MessageSquare,
  RefreshCw,
  Scissors,
  Search,
} from 'lucide-react';
import { getRagStatus } from '../../api/rag';
import { Card } from '../shared/Card';
import type { RagStatus } from '../../types';

type Tone = 'green' | 'gray' | 'blue' | 'purple';

const toneClasses: Record<Tone, string> = {
  green: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  gray: 'border-slate-200 bg-slate-100 text-slate-600',
  blue: 'border-brand-200 bg-brand-50 text-brand-700',
  purple: 'border-violet-200 bg-violet-50 text-violet-700',
};

const pipelineSteps = [
  { label: '文档上传', icon: FileUp },
  { label: '分块', icon: Scissors },
  { label: 'Embedding', icon: Database },
  { label: 'Hybrid Search', icon: Search },
  { label: 'Rerank', icon: RefreshCw },
  { label: 'LLM 回答', icon: MessageSquare },
];

function formatValue(value: string | number | boolean) {
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  return String(value);
}

function getTone(value: string | number | boolean): Tone {
  const normalized = formatValue(value).toLowerCase();
  if (normalized === 'rag_lab' || normalized === 'true') return 'green';
  if (normalized === 'legacy' || normalized === 'false') return 'gray';
  if (normalized === 'hybrid') return 'blue';
  if (normalized === 'rrf') return 'purple';
  return 'blue';
}

function ConfigBadge({ value, tone }: { value: string | number | boolean; tone?: Tone }) {
  const display = formatValue(value);
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold leading-4 ${toneClasses[tone ?? getTone(value)]}`}>
      {display}
    </span>
  );
}

export function RagEngineStatusPanel() {
  const [data, setData] = useState<RagStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const fetchStatus = async () => {
    setLoading(true);
    setError(false);
    try {
      const res = await getRagStatus();
      setData(res);
    } catch {
      setData(null);
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(false);
      try {
        const res = await getRagStatus();
        if (!cancelled) setData(res);
      } catch {
        if (!cancelled) { setData(null); setError(true); }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const engine = data?.RAG_ENGINE?.toLowerCase() ?? '';
  const connected = engine === 'rag_lab';
  const engineMessage = connected ? '当前使用增强 RAG 引擎 (rag_lab)' : '当前使用 legacy 回滚模式';

  const configItems = useMemo(() => {
    if (!data) return [];
    const items: { label: string; value: string | number | boolean }[] = [
      { label: '当前引擎', value: (data.RAG_ENGINE ?? data.rag_engine ?? '—') as string | number | boolean },
      { label: '分块策略', value: (data.CHUNK_STRATEGY ?? data.chunk_strategy ?? '—') as string | number | boolean },
      { label: '检索模式', value: (data.RAG_RETRIEVAL_MODE ?? data.retrieval_mode ?? '—') as string | number | boolean },
      { label: '融合方式', value: (data.RAG_HYBRID_FUSION ?? data.hybrid_fusion ?? '—') as string | number | boolean },
      { label: 'Rerank', value: (data.RAG_USE_RERANK ?? data.use_rerank ?? false) as string | number | boolean },
      { label: 'Rerank Top N', value: (data.RAG_RERANK_TOP_N ?? data.rerank_top_n ?? 0) as string | number | boolean },
    ];
    // Add new structured fields when available
    if (data.chunk_size != null) {
      items.push({ label: '分块大小', value: data.chunk_size });
      items.push({ label: '分块重叠', value: data.chunk_overlap ?? 0 });
    }
    if (data.embedding_model) {
      items.push({ label: 'Embedding', value: data.embedding_model });
    }
    if (data.llm_model) {
      items.push({ label: 'LLM 模型', value: data.llm_model });
    }
    return items;
  }, [data]);

  const runtimeStats = useMemo(() => {
    if (!data) return [];
    const stats = [];
    if (data.chunks_count != null) {
      stats.push({ label: '向量块数', value: data.chunks_count });
    }
    if (data.index_ready != null) {
      stats.push({ label: '索引就绪', value: data.index_ready });
    }
    if (data.last_index_time) {
      stats.push({ label: '上次索引', value: data.last_index_time.slice(0, 16).replace('T', ' ') });
    }
    return stats;
  }, [data]);

  return (
    <Card className="text-xs">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
            <Cpu className="h-5 w-5" />
          </div>
          <div>
            <h3 className="font-semibold text-text-primary text-sm">RAG 引擎状态</h3>
            <p className="mt-0.5 text-[11px] text-text-tertiary">配置与增强检索能力</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          {data && (
            <ConfigBadge value={connected ? 'rag_lab' : 'legacy'} tone={connected ? 'green' : 'gray'} />
          )}
          {loading && <Loader2 className="h-3.5 w-3.5 animate-spin text-text-tertiary" />}
        </div>
      </div>

      {data ? (
        <div className="mt-4 space-y-4">
          <div className={`flex items-center gap-2 rounded-xl border px-3 py-2.5 ${connected ? 'border-emerald-100 bg-emerald-50/70 text-emerald-700' : 'border-slate-200 bg-slate-50 text-slate-600'}`}>
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            <span className="font-medium text-xs">{engineMessage}</span>
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            {configItems.map((item) => (
              <div key={item.label} className="rounded-xl border border-surface-200 bg-surface-50 p-3">
                <div className="mb-1 text-[10px] font-medium text-text-tertiary">{item.label}</div>
                <ConfigBadge value={item.value} />
              </div>
            ))}
          </div>

          {runtimeStats.length > 0 && (
            <div className="grid grid-cols-3 gap-2">
              {runtimeStats.map((s) => (
                <div key={s.label} className="rounded-xl border border-surface-200 bg-surface-50 p-2.5 text-center">
                  <div className="text-[10px] text-text-tertiary mb-0.5">{s.label}</div>
                  <div className="text-xs font-semibold text-text-primary">
                    {typeof s.value === 'boolean' ? (s.value ? '✓' : '✗') : String(s.value)}
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="rounded-xl border border-surface-200 bg-gradient-to-r from-surface-50 to-brand-50/20 p-3.5">
            <div className="mb-2.5 text-[10px] font-semibold text-text-tertiary uppercase tracking-wide">RAG 流水线</div>
            <div className="flex flex-wrap items-center gap-1.5">
              {pipelineSteps.map((step, index) => {
                const Icon = step.icon;
                const disabled = step.label === 'Rerank' && !data.RAG_USE_RERANK;
                return (
                  <span key={step.label} className="flex items-center gap-1.5">
                    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1.5 text-[10px] font-medium ${
                      disabled
                        ? 'border-surface-200 bg-white text-text-tertiary'
                        : 'border-brand-100 bg-white text-text-secondary shadow-sm'
                    }`}>
                      <Icon className={`h-3 w-3 ${disabled ? 'text-text-tertiary' : 'text-brand-500'}`} />
                      {step.label}
                    </span>
                    {index < pipelineSteps.length - 1 && (
                      <span className="text-text-tertiary text-[10px]">→</span>
                    )}
                  </span>
                );
              })}
            </div>
          </div>
        </div>
      ) : (
        <div className="mt-4 rounded-xl border border-amber-100 bg-amber-50 px-4 py-3 text-amber-700">
          <div className="flex items-center gap-2">
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : error ? (
              <AlertCircle className="h-4 w-4" />
            ) : null}
            <span className="text-xs">
              {loading ? '正在获取 RAG 配置...' : error ? '暂时无法获取 RAG 引擎状态' : '暂无 RAG 引擎状态数据'}
            </span>
            {error && (
              <button
                onClick={fetchStatus}
                className="ml-auto text-xs font-medium text-amber-700 hover:underline"
              >
                重试
              </button>
            )}
          </div>
        </div>
      )}
    </Card>
  );
}
