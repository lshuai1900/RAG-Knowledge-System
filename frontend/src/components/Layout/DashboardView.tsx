import { useEffect, useState, useCallback } from 'react';
import { BookOpen, FileText, Cpu, Search, ArrowRight } from 'lucide-react';
import { Card } from '../shared/Card';
import type { ViewType } from './AppLayout';
import { listKnowledgeBases } from '../../api/knowledgeBase';
import { getRagStatus } from '../../api/rag';
import { useAppStore } from '../../store/appStore';
import type { RagStatus } from '../../types';

interface Props {
  onNavigate: (view: ViewType) => void;
}

export function DashboardView({ onNavigate }: Props) {
  const { knowledgeBases, setKnowledgeBases } = useAppStore();
  const [ragStatus, setRagStatus] = useState<RagStatus | null>(null);
  const [loadingKBs, setLoadingKBs] = useState(true);
  const [loadingStatus, setLoadingStatus] = useState(true);

  const fetchData = useCallback(async () => {
    setLoadingKBs(true);
    setLoadingStatus(true);
    try {
      const [kbs, status] = await Promise.allSettled([
        listKnowledgeBases(),
        getRagStatus(),
      ]);
      if (kbs.status === 'fulfilled') {
        setKnowledgeBases(kbs.value);
      }
      if (status.status === 'fulfilled') {
        setRagStatus(status.value);
      }
    } catch { /* use defaults */ }
    finally {
      setLoadingKBs(false);
      setLoadingStatus(false);
    }
  }, [setKnowledgeBases]);

  // eslint-disable-next-line react-hooks/set-state-in-effect -- initial data load
  useEffect(() => { fetchData(); }, [fetchData]);

  const totalDocs = knowledgeBases.reduce((sum, kb) => sum + (kb.document_count ?? 0), 0);
  const retrievalMode = ragStatus?.RAG_RETRIEVAL_MODE ?? '—';
  const useRerank = ragStatus?.RAG_USE_RERANK ?? false;
  const chunkStrategy = ragStatus?.CHUNK_STRATEGY ?? '—';

  const statCards = [
    { label: '知识库', value: loadingKBs ? '—' : knowledgeBases.length, icon: BookOpen, color: 'text-brand-600 bg-brand-50', view: 'knowledge-bases' as ViewType },
    { label: '文档总数', value: loadingKBs ? '—' : totalDocs, icon: FileText, color: 'text-emerald-600 bg-emerald-50', view: 'documents' as ViewType },
    { label: '检索模式', value: loadingStatus ? '—' : retrievalMode === 'hybrid' ? 'Hybrid' : retrievalMode, icon: Search, color: 'text-violet-600 bg-violet-50', view: 'rag-status' as ViewType },
    { label: 'Rerank', value: loadingStatus ? '—' : useRerank ? '已启用' : '未启用', icon: Cpu, color: 'text-amber-600 bg-amber-50', view: 'rag-status' as ViewType },
  ];

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-5xl mx-auto px-6 py-8">
        {/* Hero */}
        <div className="mb-10 animate-fade-in">
          <h1 className="text-2xl font-semibold text-text-primary">
            RAG Knowledge System
          </h1>
          <p className="mt-2 text-text-tertiary max-w-lg">
            面向中文论文/文档问答的本地 RAG 知识库系统，支持混合检索、Rerank 与引用溯源
          </p>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
          {statCards.map((card, i) => (
            <Card
              key={card.label}
              hover
              onClick={() => onNavigate(card.view)}
              className="animate-slide-up"
              style={{ animationDelay: `${i * 80}ms`, animationFillMode: 'both' }}
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-text-tertiary mb-1">{card.label}</p>
                  <p className="text-2xl font-semibold text-text-primary tabular-nums">{card.value}</p>
                </div>
                <div className={`flex h-9 w-9 items-center justify-center rounded-xl ${card.color}`}>
                  <card.icon className="h-5 w-5" />
                </div>
              </div>
            </Card>
          ))}
        </div>

        {/* Quick info + chunk strategy */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
          <Card>
            <h3 className="text-sm font-semibold text-text-primary mb-3">RAG 流水线</h3>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              {[
                { label: '文档上传', active: true },
                { label: '文本解析', active: true },
                { label: 'Chunking', active: true, extra: chunkStrategy },
                { label: 'Embedding', active: true },
                { label: 'Hybrid Search', active: retrievalMode === 'hybrid' },
                { label: 'Rerank', active: useRerank },
                { label: 'LLM 回答', active: true },
              ].map((step, i, arr) => (
                <span key={step.label} className="flex items-center gap-1.5">
                  <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 font-medium ${
                    step.active
                      ? 'border-brand-200 bg-brand-50 text-brand-700'
                      : 'border-surface-200 bg-surface-50 text-text-tertiary'
                  }`}>
                    {step.label}
                    {step.extra && (
                      <span className="text-[10px] text-text-tertiary ml-0.5">({step.extra})</span>
                    )}
                  </span>
                  {i < arr.length - 1 && (
                    <span className="text-text-tertiary">
                      <ArrowRight className="h-3 w-3" />
                    </span>
                  )}
                </span>
              ))}
            </div>
          </Card>
          <Card>
            <h3 className="text-sm font-semibold text-text-primary mb-3">快速开始</h3>
            <div className="space-y-2">
              {[
                { text: '创建知识库并上传文档', view: 'knowledge-bases' as ViewType },
                { text: '查看 RAG 引擎状态与配置', view: 'rag-status' as ViewType },
                { text: '开始智能问答对话', view: 'chat' as ViewType },
              ].map((item) => (
                <button
                  key={item.text}
                  onClick={() => onNavigate(item.view)}
                  className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm text-text-secondary hover:bg-surface-50 hover:text-brand-600 transition-colors"
                >
                  {item.text}
                  <ArrowRight className="h-3.5 w-3.5 text-text-tertiary" />
                </button>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}