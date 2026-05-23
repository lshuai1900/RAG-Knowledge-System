import { useState } from 'react';
import { ChevronDown, ChevronUp, FileText } from 'lucide-react';
import type { Source } from '../../types';

interface Props {
  sources: Source[] | string;
}

function formatScore(value: number | undefined) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '—';
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(6).replace(/0+$/, '').replace(/\.$/, '');
}

function formatText(value: string | undefined) {
  return value && value.trim() ? value : '—';
}

export function SourceCitation({ sources }: Props) {
  const [expanded, setExpanded] = useState(false);

  const parsedSources: Source[] = typeof sources === 'string'
    ? (() => { try { return JSON.parse(sources as string); } catch { return []; } })()
    : sources;

  if (!Array.isArray(parsedSources) || parsedSources.length === 0) return null;

  return (
    <div className="mt-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 transition-colors"
      >
        {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        {parsedSources.length} 个来源
      </button>
      {expanded && (
        <div className="mt-2 space-y-2 max-h-60 overflow-y-auto">
          {parsedSources.map((src, i) => {
            const source = src.source ?? src.metadata?.source ?? src.document_name;
            const denseScore = src.dense_score ?? src.vector_score ?? src.similarity_score;
            const sparseScore = src.sparse_score ?? src.bm25_score_norm ?? src.bm25_score;
            const fusionScore = src.fusion_score ?? src.hybrid_score ?? src.effective_score;
            const chunkStrategy = src.chunk_strategy ?? src.metadata?.chunk_strategy;

            return (
              <div key={i} className="bg-gray-50 rounded-lg p-3 text-xs">
                <div className="flex items-center gap-1.5 text-gray-500 mb-1">
                  <FileText className="w-3 h-3" />
                  <span className="font-medium">{src.document_name}</span>
                </div>
                <div className="grid grid-cols-[auto,1fr] gap-x-3 gap-y-0.5 mb-2 text-gray-500">
                  <span>source</span>
                  <span className="truncate text-gray-700" title={source}>{formatText(source)}</span>

                  <span>score</span>
                  <span className="text-gray-700">{formatScore(src.score)}</span>

                  <span>dense_score</span>
                  <span className="text-gray-700">{formatScore(denseScore)}</span>

                  <span>sparse_score</span>
                  <span className="text-gray-700">{formatScore(sparseScore)}</span>

                  <span>fusion_score</span>
                  <span className="text-gray-700">{formatScore(fusionScore)}</span>

                  <span>rerank_score</span>
                  <span className="text-gray-700">{formatScore(src.rerank_score)}</span>

                  <span>chunk_strategy</span>
                  <span className="truncate text-gray-700" title={chunkStrategy}>{formatText(chunkStrategy)}</span>
                </div>
                <p className="text-gray-600 line-clamp-4">{src.content}</p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
