import { useState } from 'react';
import { ChevronDown, ChevronUp, FileText } from 'lucide-react';
import type { Source } from '../../types';

interface Props {
  sources: Source[];
}

export function SourceCitation({ sources }: Props) {
  const [expanded, setExpanded] = useState(false);

  // Handle case where sources is a JSON string from backend
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
          {parsedSources.map((src, i) => (
            <div key={i} className="bg-gray-50 rounded-lg p-3 text-xs">
              <div className="flex items-center gap-1.5 text-gray-500 mb-1">
                <FileText className="w-3 h-3" />
                <span className="font-medium">{src.document_name}</span>
                <span className="text-gray-300">|</span>
                <span>相似度: {src.score}</span>
              </div>
              <p className="text-gray-600 line-clamp-4">{src.content}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
