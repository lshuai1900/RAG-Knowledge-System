import { useState, type ReactNode } from 'react';
import { BarChart3, ChevronDown, ChevronUp, FileText, Layers, Link2 } from 'lucide-react';
import type { Source } from '../../types';

interface Props {
  sources: Source[] | string;
}

function parseSources(sources: Source[] | string): Source[] {
  if (typeof sources !== 'string') return sources;
  try {
    const parsed = JSON.parse(sources);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function getScore(value: number | undefined) {
  if (typeof value !== 'number' || Number.isNaN(value)) return undefined;
  return value;
}

function formatScore(value: number | undefined) {
  const score = getScore(value);
  return typeof score === 'number' ? score.toFixed(3) : '-';
}

function formatText(value: string | undefined) {
  return value && value.trim() ? value : '-';
}

function Chip({ children, tone = 'gray' }: { children: ReactNode; tone?: 'gray' | 'blue' | 'emerald' | 'violet' }) {
  const classes = {
    gray: 'border-surface-200 bg-surface-50 text-text-secondary',
    blue: 'border-brand-200 bg-brand-50 text-brand-700',
    emerald: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    violet: 'border-violet-200 bg-violet-50 text-violet-700',
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
  const rerankScore = source.rerank_score;
  const hasAdvanced = [denseScore, sparseScore, fusionScore, rerankScore].some((v) => v != null);

  const advancedScores = [
    { label: 'Dense', value: denseScore },
    { label: 'Sparse', value: sparseScore },
    { label: 'Fusion', value: fusionScore },
    { label: 'Rerank', value: rerankScore },
  ].filter((s) => s.value != null);

  const totalScore = formatScore(source.score);
  const scoreNum = getScore(source.score);

  return (
    <article className="rounded-xl border border-surface-200 bg-white p-3.5 text-xs shadow-card transition-all hover:border-brand-200 hover:shadow-card-hover">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5 min-w-0 flex-1">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-surface-100 text-text-tertiary mt-0.5">
            <FileText className="h-3.5 w-3.5" />
          </div>
          <div className="min-w-0">
            <div className="font-semibold text-text-primary truncate">
              {formatText(source.document_name || sourcePath)}
            </div>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-[10px] text-text-tertiary">来源 #{index + 1}</span>
              {chunkStrategy && (
                <Chip tone="blue">{chunkStrategy}</Chip>
              )}
            </div>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
          <Chip tone={scoreNum != null && scoreNum > 0.7 ? 'emerald' : scoreNum != null && scoreNum > 0.4 ? 'blue' : 'gray'}>
            score {totalScore}
          </Chip>
        </div>
      </div>

      <div className="mt-3 rounded-lg border border-surface-100 bg-surface-50/80 p-2.5">
        <div className="mb-1 flex items-center gap-1.5 text-[10px] font-medium text-text-tertiary">
          <Layers className="h-3 w-3" />
          内容摘要
        </div>
        <p className="text-xs leading-5 text-text-secondary line-clamp-4">
          {formatText(source.content)}
        </p>
      </div>

      {hasAdvanced && (
        <>
          <button
            type="button"
            onClick={() => setAdvancedOpen((open) => !open)}
            className="mt-2.5 flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-[11px] font-medium text-text-tertiary hover:bg-surface-50 hover:text-text-secondary transition-colors"
          >
            <span className="flex items-center gap-1.5">
              <BarChart3 className="h-3.5 w-3.5" />
              检索分数详情
            </span>
            {advancedOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </button>

          {advancedOpen && (
            <div className="mt-1 grid grid-cols-2 gap-2 rounded-lg border border-surface-100 bg-surface-50 p-2.5">
              {advancedScores.map((item) => (
                <div key={item.label} className="rounded-md bg-white px-2.5 py-1.5 border border-surface-100">
                  <div className="text-[10px] text-text-tertiary">{item.label}</div>
                  <div className="mt-0.5 font-semibold tabular-nums text-text-primary text-xs">
                    {formatScore(item.value)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
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
        className="inline-flex items-center gap-2 rounded-full border border-surface-200 bg-white px-3 py-1.5 text-xs font-medium text-text-secondary shadow-card hover:border-brand-200 hover:text-brand-700 transition-all"
      >
        <Link2 className="h-3.5 w-3.5" />
        {parsedSources.length} 个引用来源
        {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
      </button>
      {expanded && (
        <div className="mt-2.5 space-y-2 max-h-96 overflow-y-auto pr-1">
          {parsedSources.map((source, index) => (
            <SourceCard key={`${source.chunk_index ?? index}-${index}`} source={source} index={index} />
          ))}
        </div>
      )}
    </div>
  );
}
