import { useEffect, useState, useCallback } from 'react';
import {
  BookOpen, Cpu, Search, ArrowRight, Layers,
  Zap, Shield, Activity, AlertCircle, WifiOff, RefreshCw,
} from 'lucide-react';
import { Card } from '../shared/Card';
import { Badge } from '../shared/Badge';
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
  const [statusError, setStatusError] = useState(false);
  const [statusErrorMsg, setStatusErrorMsg] = useState('');

  const fetchData = useCallback(async () => {
    setLoadingKBs(true);
    setLoadingStatus(true);
    setStatusError(false);
    setStatusErrorMsg('');
    try {
      const [kbs, status] = await Promise.allSettled([
        listKnowledgeBases(),
        getRagStatus(),
      ]);
      if (kbs.status === 'fulfilled') setKnowledgeBases(kbs.value);
      if (status.status === 'fulfilled') {
        setRagStatus(status.value);
        setStatusError(false);
      } else {
        setStatusError(true);
        setStatusErrorMsg(status.reason?.message || '无法连接后端服务');
      }
    } catch {
      setStatusError(true);
      setStatusErrorMsg('网络请求失败');
    } finally {
      setLoadingKBs(false);
      setLoadingStatus(false);
    }
  }, [setKnowledgeBases]);

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { fetchData(); }, [fetchData]);

  const statusOk = !statusError && ragStatus !== null;
  const documentCount = ragStatus?.documents_count
    ?? knowledgeBases.reduce((sum, kb) => sum + (kb.document_count ?? 0), 0);
  const provider = statusOk ? (ragStatus!.embedding_provider || ragStatus!.RAG_ENGINE || '—') : '—';
  const retrievalMode = statusOk ? (ragStatus!.retrieval_mode || ragStatus!.RAG_RETRIEVAL_MODE || '—') : '—';
  const useRerank = statusOk ? (ragStatus!.use_rerank ?? ragStatus!.RAG_USE_RERANK ?? false) : false;
  const chunkStrategy = statusOk ? (ragStatus!.chunk_strategy || ragStatus!.CHUNK_STRATEGY || '—') : '—';
  const chunksCount = statusOk ? (ragStatus!.chunks_count ?? 0) : null;
  const indexReady = statusOk ? (ragStatus!.index_ready ?? false) : null;
  const health = statusOk ? (ragStatus!.health || 'unknown') : null;
  const isHash = provider === 'hash' || provider === 'hash-sha256-256d';

  const statCards = [
    {
      label: '知识库', value: loadingKBs ? '...' : knowledgeBases.length,
      icon: BookOpen, color: 'text-brand-600 bg-brand-50',
      sub: !statusOk && !loadingKBs ? '后端未连接'
        : knowledgeBases.length === 0 ? '创建第一个知识库'
        : `${documentCount} 篇文档`,
      view: 'knowledge-bases' as ViewType,
      ok: true,
    },
    {
      label: 'Chunk 数量',
      value: loadingStatus ? '...' : !statusOk ? '—' : chunksCount ?? 0,
      icon: Layers, color: 'text-emerald-600 bg-emerald-50',
      sub: !statusOk ? '状态不可用'
        : indexReady ? '索引就绪'
        : (chunksCount ?? 0) > 0 ? '索引待建'
        : '上传文档建立索引',
      view: 'documents' as ViewType,
      ok: statusOk,
    },
    {
      label: 'Embedding',
      value: loadingStatus ? '...' : !statusOk ? '离线' : provider,
      icon: Cpu, color: isHash ? 'text-amber-600 bg-amber-50' : 'text-violet-600 bg-violet-50',
      sub: !statusOk ? '后端未连接'
        : isHash ? 'Hash 演示模式'
        : '远程 Embedding',
      view: 'rag-status' as ViewType,
      ok: true,
    },
    {
      label: '检索模式', value: loadingStatus ? '...' : !statusOk ? '离线' : retrievalMode,
      icon: Search, color: 'text-sky-600 bg-sky-50',
      sub: !statusOk ? '后端未连接' : useRerank ? 'Rerank 已启用' : 'Rerank 未启用',
      view: 'rag-status' as ViewType,
      ok: statusOk,
    },
  ];

  const pipelineSteps = [
    { label: '文档上传', sub: 'PDF/TXT/MD/DOCX', active: true },
    { label: 'ParserRegistry', sub: 'auto', active: true },
    { label: 'ChunkingDispatcher', sub: statusOk ? chunkStrategy : 'unavailable', active: statusOk },
    { label: 'EmbeddingProvider', sub: statusOk ? (isHash ? 'hash 256d' : provider) : 'unavailable', active: statusOk },
    { label: 'VectorStore', sub: statusOk ? (indexReady ? `${chunksCount} chunks` : 'no index') : 'unavailable', active: statusOk && !!indexReady },
    { label: 'RetrievalPipeline', sub: statusOk ? retrievalMode : 'unavailable', active: statusOk && !!indexReady },
    { label: 'SourceBuilder', sub: statusOk ? (indexReady ? 'ready' : 'pending') : 'unavailable', active: statusOk && !!indexReady },
    { label: 'LLM / Fallback', sub: 'retrieval-only', active: true },
  ];

  const quickStarts = [
    { text: '创建知识库并上传文档', desc: '支持 PDF、Markdown、DOCX、TXT', view: 'knowledge-bases' as ViewType },
    { text: '使用 Hash 模式自动建立索引', desc: '零 API Key 演示，无需配置', view: 'documents' as ViewType },
    { text: '在智能问答中查看 answer + sources', desc: '引用溯源、分数详情', view: 'chat' as ViewType },
    { text: '检查 RAG Engine 状态', desc: 'chunk 数、embedding、检索配置', view: 'rag-status' as ViewType },
  ];

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-[1180px] mx-auto px-6 py-8">
        {/* Hero */}
        <div className="mb-8 animate-fade-in">
          <h1 className="text-2xl font-semibold text-text-primary">
            RAG Knowledge System
          </h1>
          <p className="mt-2 text-text-tertiary max-w-2xl">
            基于 Yuxi-style 架构的本地 RAG 知识库系统，支持文档解析、多策略分块、Hash Embedding 演示模式、Hybrid Search、引用溯源与状态可观测。
          </p>
          <div className="flex flex-wrap gap-2 mt-4">
            {statusError ? (
              <>
                <Badge variant="error">
                  <WifiOff className="h-3 w-3 inline mr-0.5" />
                  Backend Disconnected
                </Badge>
                <button
                  onClick={fetchData}
                  className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-semibold rounded-full border border-red-200 bg-red-50 text-red-700 hover:bg-red-100 transition-colors"
                >
                  <RefreshCw className="h-3 w-3" />
                  点击重试
                  {statusErrorMsg && <span className="ml-1 font-normal opacity-70">— {statusErrorMsg}</span>}
                </button>
              </>
            ) : (
              <>
                <Badge variant={isHash ? 'warning' : 'brand'}>
                  {isHash ? 'Hash Demo Ready' : 'Remote Embedding'}
                </Badge>
                <Badge variant={indexReady ? 'success' : 'gray'}>
                  {indexReady ? 'Index Ready' : 'No Index'}
                </Badge>
                <Badge variant="brand">Yuxi-style Pipeline</Badge>
              </>
            )}
          </div>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {statCards.map((card, i) => (
            <Card
              key={card.label}
              hover={card.ok}
              onClick={() => card.ok && onNavigate(card.view)}
              style={{ animationDelay: `${i * 60}ms`, animationFillMode: 'both' }}
              className={`animate-slide-up ${!card.ok ? 'opacity-60' : ''}`}
            >
              <div className="flex items-start justify-between">
                <div className="min-w-0">
                  <p className="text-xs font-medium text-text-tertiary mb-1">{card.label}</p>
                  <p className="text-xl font-semibold text-text-primary tabular-nums truncate">
                    {card.value}
                  </p>
                  <p className="text-[11px] text-text-tertiary mt-0.5">{card.sub}</p>
                </div>
                <div className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl ${card.color}`}>
                  <card.icon className="h-5 w-5" />
                </div>
              </div>
            </Card>
          ))}
        </div>

        {/* Main content grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-8">
          {/* Pipeline */}
          <Card className="lg:col-span-2">
            <div className="flex items-center gap-2 mb-4">
              <Activity className="h-4 w-4 text-brand-600" />
              <h3 className="text-sm font-semibold text-text-primary">RAG 流水线</h3>
            </div>
            <div className="flex flex-wrap items-center gap-1.5 text-xs">
              {pipelineSteps.map((step, i, arr) => (
                <span key={step.label} className="flex items-center gap-1">
                  <span className={`inline-flex flex-col items-center rounded-lg border px-2 py-1.5 ${
                    step.active
                      ? 'border-brand-200 bg-brand-50 text-text-primary'
                      : 'border-surface-200 bg-surface-50 text-text-tertiary'
                  }`}>
                    <span className="text-[11px] font-medium">{step.label}</span>
                    <span className="text-[9px] text-text-tertiary">{step.sub}</span>
                  </span>
                  {i < arr.length - 1 && (
                    <ArrowRight className="h-3 w-3 text-text-tertiary flex-shrink-0" />
                  )}
                </span>
              ))}
            </div>
          </Card>

          {/* Health */}
          <Card>
            <div className="flex items-center gap-2 mb-3">
              <Shield className={`h-4 w-4 ${
                !statusOk ? 'text-red-500' :
                health === 'healthy' ? 'text-emerald-500' :
                health === 'error' ? 'text-red-500' : 'text-amber-500'
              }`} />
              <h3 className="text-sm font-semibold text-text-primary">系统状态</h3>
            </div>
            {!statusOk ? (
              <div className="text-xs text-center py-4 text-text-tertiary">
                <WifiOff className="h-5 w-5 mx-auto mb-2 opacity-40" />
                <p>后端未连接</p>
                <button onClick={fetchData} className="mt-2 text-brand-600 hover:underline">
                  点击重试
                </button>
              </div>
            ) : (
              <div className="space-y-2 text-xs">
                {[
                  { label: '健康状态', value: health === 'healthy' ? 'Healthy' : health, ok: health === 'healthy' },
                  { label: 'Embedding', value: `${provider} · ${ragStatus?.embedding_dim || '—'}d` },
                  { label: 'Chunk 策略', value: chunkStrategy },
                  { label: '文档数', value: documentCount },
                  { label: 'Chunk 总数', value: chunksCount ?? 0 },
                  { label: '索引就绪', value: indexReady ? '是' : '否', ok: !!indexReady },
                  { label: '最近索引', value: ragStatus?.last_index_time?.slice(0, 16)?.replace('T', ' ') || '—' },
                ].map((row) => (
                  <div key={row.label} className="flex justify-between items-center">
                    <span className="text-text-tertiary">{row.label}</span>
                    <span className={`font-medium ${
                      row.ok === true ? 'text-emerald-600' :
                      row.ok === false ? 'text-amber-600' : 'text-text-primary'
                    }`}>
                      {row.value}
                    </span>
                  </div>
                ))}
                {(ragStatus?.warnings?.length ?? 0) > 0 ? (
                  <div className="mt-2 pt-2 border-t border-surface-100">
                    {ragStatus!.warnings!.map((w: string, i: number) => (
                      <div key={i} className="text-[11px] text-amber-600 flex items-center gap-1">
                        <AlertCircle className="h-3 w-3 flex-shrink-0" />{w}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="mt-2 pt-2 border-t border-surface-100 text-[11px] text-text-tertiary">
                    <Zap className="h-3 w-3 inline mr-1" />暂无警告
                  </div>
                )}
              </div>
            )}
          </Card>
        </div>

        {/* Bottom row: Quick start + Hash demo info */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <Card>
            <h3 className="text-sm font-semibold text-text-primary mb-3">快速开始</h3>
            <div className="space-y-1">
              {quickStarts.map((item, i) => (
                <button
                  key={item.text}
                  onClick={() => onNavigate(item.view)}
                  className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm text-text-secondary hover:bg-surface-50 hover:text-brand-600 transition-colors text-left"
                >
                  <div>
                    <span className="text-xs font-medium text-text-tertiary mr-2">{i + 1}.</span>
                    {item.text}
                    <span className="block text-[11px] text-text-tertiary ml-5 mt-0.5">{item.desc}</span>
                  </div>
                  <ArrowRight className="h-3.5 w-3.5 text-text-tertiary flex-shrink-0" />
                </button>
              ))}
            </div>
          </Card>

          <Card>
            <div className="flex items-center gap-2 mb-3">
              <Zap className="h-4 w-4 text-amber-500" />
              <h3 className="text-sm font-semibold text-text-primary">无 API Key 演示模式</h3>
            </div>
            <div className="text-xs text-text-secondary space-y-2">
              <p>当前默认支持 <strong>Hash Embedding</strong> 演示模式：</p>
              <ul className="space-y-1.5 text-text-tertiary">
                <li className="flex items-start gap-2">
                  <span className="text-emerald-500 mt-0.5">✓</span>
                  无需任何 API Key，clone 即用
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-emerald-500 mt-0.5">✓</span>
                  完整跑通上传 → 分块 → 索引 → 检索 → sources
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-amber-500 mt-0.5">⚠</span>
                  Hash 伪向量仅用于开发演示，不代表真实语义检索质量
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-text-tertiary mt-0.5">→</span>
                  生产使用请将 <code className="bg-surface-100 px-1 rounded text-[11px]">EMBEDDING_PROVIDER</code> 设为
                  <code className="bg-surface-100 px-1 rounded text-[11px]">openai_compatible</code> 或 <code className="bg-surface-100 px-1 rounded text-[11px]">dashscope</code>，并配置对应的 Embedding API
                </li>
              </ul>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
