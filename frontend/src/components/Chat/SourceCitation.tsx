import { useState, type ReactNode } from 'react';
import { BarChart3, ChevronDown, ChevronUp, FileText, Layers } from 'lucide-react';
import type { Source } from '../../types';

interface Props {
  sources: Source[] | string;
}

function parseSources(sources: Source[] | string): Source[] {
  if (typeof sources !== 'string') {
    return sources;
  }
  try {
    const parsed = JSON.parse(sources);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function getScore(value: number | undefined) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return undefined;
  }
  return value;
}

function formatScore(value: number | undefined) {
  const score = getScore(value);
  return typeof score === 'number' ? score.toFixed(3) : '-';
}

function formatText(value: string | undefined) {
  return value && value.trim() ? value : '-';
}

function Chip({ children, tone = 'gray' }: { children: ReactNode; tone?: 'gray' | 'blue' | 'emerald' }) {
  const classes = {
    gray: 'border-gray-200 bg-gray-50 text-gray-600',
    blue: 'border-sky-200 bg-sky-50 text-sky-700',
    emerald: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  }[tone];
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold leading-4 ${classes}`}>
      {children}
    </span>
  );
}

function SourceCard({ source, index }: { source: Source; index: number }) {
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const sourcePath = source.source ?? source.metadata?.source ?? source.document_name;
  const chunkStrategy = source.chunk_strategy ?? source.metadata?.chunk_strategy;
  const denseScore = source.dense_score ?? source.vector_score ?? source.similarity_score;
  const sparseScore = source.sparse_score ?? source.bm25_score_norm ?? source.bm25_score;
  const fusionScore = source.fusion_score ?? source.hybrid_score ?? source.effective_score;
  const advancedScores = [
    { label: 'dense_score', value: denseScore },
    { label: 'sparse_score', value: sparseScore },
    { label: 'fusion_score', value: fusionScore },
    { label: 'rerank_score', value: source.rerank_score },
  ];

  return (
    <article className="rounded-xl border border-gray-200 bg-white p-3 text-xs shadow-sm transition-colors hover:border-sky-200 hover:bg-sky-50/20">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 text-gray-700">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-gray-100 text-gray-500">
              <FileText className="h-3.5 w-3.5" />
            </span>
            <div className="min-w-0">
              <div className="truncate font-semibold text-gray-800" title={sourcePath}>
                {formatText(source.document_name || sourcePath)}
              </div>
              <div className="mt-0.5 truncate text-[10px] text-gray-400" title={sourcePath}>
                source #{index + 1}
              </div>
            </div>
          </div>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <Chip tone="emerald">score {formatScore(source.score)}</Chip>
          <Chip tone={chunkStrategy ? 'blue' : 'gray'}>{formatText(chunkStrategy)}</Chip>
        </div>
      </div>

      <div className="mt-3 rounded-lg border border-gray-100 bg-gray-50/80 p-2.5">
        <div className="mb-1 flex items-center gap-1 text-[10px] font-medium text-gray-400">
          <Layers className="h-3 w-3" />
          上下文摘要
        </div>
        <p className="text-xs leading-5 text-gray-600 line-clamp-4">{formatText(source.content)}</p>
      </div>

      <button
        type="button"
        onClick={() => setAdvancedOpen((open) => !open)}
        className="mt-2 flex w-full items-center justify-between rounded-lg px-1 py-1 text-[11px] font-medium text-gray-500 transition-colors hover:bg-gray-50 hover:text-gray-700"
      >
        <span className="flex items-center gap-1.5">
          <BarChart3 className="h-3.5 w-3.5" />
          高级分数
        </span>
        {advancedOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
      </button>

      {advancedOpen && (
        <div className="mt-1 grid grid-cols-2 gap-2 rounded-lg border border-gray-100 bg-gray-50 p-2">
          {advancedScores.map((item) => (
            <div key={item.label} className="rounded-md bg-white px-2 py-1.5">
              <div className="text-[10px] text-gray-400">{item.label}</div>
              <div className="mt-0.5 font-semibold tabular-nums text-gray-700">{formatScore(item.value)}</div>
            </div>
          ))}
        </div>
      )}
    </article>
  );
}

export function SourceCitation({ sources }: Props) {
  const [expanded, setExpanded] = useState(false);
  const parsedSources = parseSources(sources);

  if (!Array.isArray(parsedSources) || parsedSources.length === 0) return null;

  return (
    <div className="mt-3">
      <button
        onClick={() => setExpanded(!expanded)}
        className="inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-white px-2.5 py-1 text-xs font-medium text-gray-500 shadow-sm transition-colors hover:border-sky-200 hover:text-sky-700"
      >
        {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        {parsedSources.length} 个来源
      </button>
      {expanded && (
        <div className="mt-2 space-y-2 max-h-80 overflow-y-auto pr-1">
          {parsedSources.map((source, index) => (
            <SourceCard key={`${source.chunk_index}-${index}`} source={source} index={index} />
          ))}
        </div>
      )}
    </div>
  );
}
