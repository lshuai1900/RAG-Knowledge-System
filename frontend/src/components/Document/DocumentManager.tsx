import { useState } from 'react';
import { RefreshCw, Loader2, X, AlertCircle, CheckCircle2 } from 'lucide-react';
import { rebuildIndex } from '../../api/knowledgeBase';
import { useAppStore } from '../../store/appStore';
import { ConfirmModal } from '../shared/ConfirmModal';
import { toast } from '../shared/toast';
import type { RebuildIndexResponse } from '../../types';

export function DocumentManager() {
  const { activeKnowledgeBaseId } = useAppStore();
  const [rebuildConfirm, setRebuildConfirm] = useState(false);
  const [rebuilding, setRebuilding] = useState(false);
  const [rebuildResult, setRebuildResult] = useState<RebuildIndexResponse | null>(null);

  const handleRebuild = async () => {
    if (!activeKnowledgeBaseId) return;
    setRebuildConfirm(false);
    setRebuilding(true);
    try {
      const result = await rebuildIndex(activeKnowledgeBaseId);
      setRebuildResult(result);
      if (result.warnings.length > 0) {
        result.warnings.forEach((w) => toast('warning', w));
      }
      if (result.status === 'completed') {
        toast('success', `索引重建完成：${result.success_documents} 个文档，${result.chunk_count} 个向量块`);
      } else if (result.status === 'partial') {
        toast('warning', `索引重建部分完成：${result.success_documents}/${result.document_count} 成功`);
      } else {
        toast('error', '索引重建失败');
      }
      window.dispatchEvent(new Event('documents-changed'));
    } catch {
      toast('error', '重建索引失败');
    } finally {
      setRebuilding(false);
    }
  };

  if (!activeKnowledgeBaseId) return null;

  return (
    <>
      <ConfirmModal
        open={rebuildConfirm}
        title="重建索引"
        message="确定重建索引？\n\n重建期间问答结果可能暂时不稳定。将重新解析所有文档并重建向量索引和 BM25 索引。"
        confirmLabel="开始重建"
        loading={rebuilding}
        onConfirm={handleRebuild}
        onCancel={() => setRebuildConfirm(false)}
      />

      <button
        onClick={() => setRebuildConfirm(true)}
        disabled={rebuilding}
        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium text-text-secondary bg-surface-50 border border-surface-200 rounded-xl hover:bg-surface-100 hover:text-text-primary disabled:opacity-50 transition-colors"
      >
        {rebuilding ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <RefreshCw className="h-4 w-4" />
        )}
        {rebuilding ? '重建中...' : '重建索引'}
      </button>

      {rebuildResult && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setRebuildResult(null)} />
          <div className="relative bg-white rounded-2xl shadow-elevated max-w-sm w-full mx-4 p-6 animate-slide-up">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                {rebuildResult.status === 'completed' ? (
                  <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                ) : rebuildResult.status === 'partial' ? (
                  <AlertCircle className="h-5 w-5 text-amber-500" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-red-500" />
                )}
                <h3 className="text-lg font-semibold text-text-primary">重建结果</h3>
              </div>
              <button
                className="p-1 rounded-lg text-text-tertiary hover:text-text-secondary hover:bg-surface-50"
                onClick={() => setRebuildResult(null)}
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-2 text-sm">
              {[
                { label: '状态', value: rebuildResult.status, color: rebuildResult.status === 'completed' ? 'text-emerald-600' : rebuildResult.status === 'partial' ? 'text-amber-600' : 'text-red-600' },
                { label: '文档总数', value: rebuildResult.document_count },
                { label: '成功', value: rebuildResult.success_documents, color: 'text-emerald-600' },
                { label: '向量块数', value: rebuildResult.chunk_count },
                { label: 'BM25 块数', value: rebuildResult.bm25_chunk_count },
              ].map(({ label, value, color }) => (
                <div key={label} className="flex justify-between">
                  <span className="text-text-tertiary">{label}</span>
                  <span className={`font-medium ${color ?? 'text-text-primary'}`}>{value}</span>
                </div>
              ))}
            </div>

            {rebuildResult.failed_documents.length > 0 && (
              <div className="mt-3 pt-3 border-t border-surface-100">
                <span className="text-sm font-medium text-red-600">失败文档：</span>
                {rebuildResult.failed_documents.map((fd) => (
                  <div key={fd.doc_id} className="mt-1 text-xs text-red-500">
                    <span className="font-medium">{fd.filename}</span>: {fd.error}
                  </div>
                ))}
              </div>
            )}

            {rebuildResult.warnings.length > 0 && (
              <div className="mt-2 pt-2 border-t border-surface-100">
                {rebuildResult.warnings.map((w, i) => (
                  <div key={i} className="text-xs text-amber-600">{w}</div>
                ))}
              </div>
            )}

            <button
              className="mt-4 w-full px-4 py-2.5 text-sm font-medium bg-surface-100 text-text-secondary rounded-xl hover:bg-surface-200 transition-colors"
              onClick={() => setRebuildResult(null)}
            >
              关闭
            </button>
          </div>
        </div>
      )}
    </>
  );
}
