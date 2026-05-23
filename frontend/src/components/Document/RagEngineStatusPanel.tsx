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
import type { RagStatus } from '../../types';

type Tone = 'green' | 'gray' | 'blue' | 'purple';

const toneClasses: Record<Tone, string> = {
  green: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  gray: 'border-slate-200 bg-slate-100 text-slate-600',
  blue: 'border-sky-200 bg-sky-50 text-sky-700',
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
  if (typeof value === 'boolean') {
    return value ? 'true' : 'false';
  }
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

function Badge({ value, tone }: { value: string | number | boolean; tone?: Tone }) {
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

  useEffect(() => {
    let cancelled = false;

    const fetchStatus = async () => {
      setLoading(true);
      setError(false);
      try {
        const res = await getRagStatus();
        if (!cancelled) {
          setData(res);
        }
      } catch {
        if (!cancelled) {
          setData(null);
          setError(true);
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

  const engine = data?.RAG_ENGINE?.toLowerCase() ?? '';
  const connected = engine === 'rag_lab';
  const engineMessage = connected ? '当前使用增强 RAG 引擎' : '当前使用 legacy 回滚模式';

  const configItems = useMemo(() => {
    if (!data) return [];
    return [
      { label: '当前引擎', value: data.RAG_ENGINE },
      { label: '分块策略', value: data.CHUNK_STRATEGY },
      { label: '检索模式', value: data.RAG_RETRIEVAL_MODE },
      { label: '融合方式', value: data.RAG_HYBRID_FUSION },
      { label: 'Rerank', value: data.RAG_USE_RERANK },
      { label: 'Rerank Top N', value: data.RAG_RERANK_TOP_N },
    ];
  }, [data]);

  return (
    <section className="mx-2 rounded-xl border border-gray-200 bg-white p-3 text-xs shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-sky-50 text-sky-600">
            <Cpu className="h-3.5 w-3.5" />
          </span>
          <div>
            <div className="font-semibold text-gray-900">RAG 引擎状态</div>
            <div className="mt-0.5 text-[11px] text-gray-400">配置与增强能力</div>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <Badge value={connected ? '已接入' : '未接入'} tone={connected ? 'green' : 'gray'} />
          {data && <Badge value={data.RAG_ENGINE} />}
          {loading && <Loader2 className="h-3.5 w-3.5 animate-spin text-gray-400" />}
        </div>
      </div>

      {data ? (
        <div className="mt-3 space-y-3">
          <div className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-2 ${connected ? 'border-emerald-100 bg-emerald-50/70 text-emerald-700' : 'border-slate-200 bg-slate-50 text-slate-600'}`}>
            <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
            <span className="font-medium">{engineMessage}</span>
          </div>

          <div className="grid grid-cols-2 gap-2">
            {configItems.map((item) => (
              <div key={item.label} className="rounded-lg border border-gray-200 bg-gray-50/80 p-2">
                <div className="mb-1 text-[10px] font-medium text-gray-400">{item.label}</div>
                <Badge value={item.value} />
              </div>
            ))}
          </div>

          <div className="rounded-lg border border-gray-200 bg-gradient-to-r from-gray-50 to-sky-50/40 p-2.5">
            <div className="mb-2 text-[10px] font-medium text-gray-400">RAG 流程</div>
            <div className="flex flex-wrap items-center gap-1.5">
              {pipelineSteps.map((step, index) => {
                const Icon = step.icon;
                const disabled = step.label === 'Rerank' && !data.RAG_USE_RERANK;
                return (
                  <div key={step.label} className="flex items-center gap-1.5">
                    <div className={`flex items-center gap-1 rounded-full border px-2 py-1 ${disabled ? 'border-gray-200 bg-white text-gray-400' : 'border-sky-100 bg-white text-gray-600'}`}>
                      <Icon className="h-3 w-3" />
                      <span className="text-[10px] font-medium">{step.label}</span>
                    </div>
                    {index < pipelineSteps.length - 1 && <span className="text-gray-300">→</span>}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      ) : (
        <div className="mt-3 rounded-lg border border-amber-100 bg-amber-50 px-2.5 py-2 text-amber-700">
          <div className="flex items-center gap-1.5">
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <AlertCircle className="h-3.5 w-3.5" />}
            <span>{loading ? '正在读取 RAG 配置...' : error ? '暂时无法获取 RAG 引擎状态' : '暂无 RAG 引擎状态'}</span>
          </div>
        </div>
      )}
    </section>
  );
}
