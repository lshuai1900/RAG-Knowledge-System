import { useState } from 'react';
import { RefreshCw, Loader2, X, AlertCircle, CheckCircle2 } from 'lucide-react';
import { DocumentUploader } from './DocumentUploader';
import { DocumentList } from './DocumentList';
import { IndexStatusPanel } from './IndexStatusPanel';
import { ConfirmModal } from '../shared/ConfirmModal';
import { toast } from '../shared/Toast';
import { rebuildIndex } from '../../api/knowledgeBase';
import { useAppStore } from '../../store/appStore';
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
      // Trigger document list refresh
      window.dispatchEvent(new Event('documents-changed'));
    } catch {
      toast('error', '重建索引失败');
    } finally {
      setRebuilding(false);
    }
  };

  const statusBadge = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle2 className="w-5 h-5 text-green-500" />;
      case 'partial': return <AlertCircle className="w-5 h-5 text-yellow-500" />;
      case 'failed': return <AlertCircle className="w-5 h-5 text-red-500" />;
      default: return null;
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between px-2">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">文档</span>
        {activeKnowledgeBaseId && (
          <button
            onClick={() => setRebuildConfirm(true)}
            disabled={rebuilding}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-blue-600 transition-colors disabled:opacity-50"
            title="重建索引"
          >
            {rebuilding ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <RefreshCw className="w-3 h-3" />
            )}
            重建索引
          </button>
        )}
      </div>

      <IndexStatusPanel />

      <DocumentUploader />
      <DocumentList />

      <ConfirmModal
        open={rebuildConfirm}
        title="重建索引"
        message="确定重建索引？\n\n重建期间问答结果可能暂时不稳定。将重新解析所有文档并重建向量索引和 BM25 索引。"
        confirmLabel="开始重建"
        loading={rebuilding}
        onConfirm={handleRebuild}
        onCancel={() => setRebuildConfirm(false)}
      />

      {/* Rebuild result modal */}
      {rebuildResult && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/40" onClick={() => setRebuildResult(null)} />
          <div className="relative bg-white rounded-xl shadow-xl max-w-sm w-full mx-4 p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                {statusBadge(rebuildResult.status)}
                <h3 className="text-lg font-semibold text-gray-900">重建结果</h3>
              </div>
              <button
                className="text-gray-400 hover:text-gray-600"
                onClick={() => setRebuildResult(null)}
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-2 text-sm text-gray-600">
              <div className="flex justify-between">
                <span>状态</span>
                <span className={`font-medium ${
                  rebuildResult.status === 'completed' ? 'text-green-600' :
                  rebuildResult.status === 'partial' ? 'text-yellow-600' : 'text-red-600'
                }`}>{rebuildResult.status}</span>
              </div>
              <div className="flex justify-between">
                <span>文档总数</span>
                <span>{rebuildResult.document_count}</span>
              </div>
              <div className="flex justify-between">
                <span>成功</span>
                <span className="text-green-600">{rebuildResult.success_documents}</span>
              </div>
              <div className="flex justify-between">
                <span>向量块数</span>
                <span>{rebuildResult.chunk_count}</span>
              </div>
              <div className="flex justify-between">
                <span>BM25 块数</span>
                <span>{rebuildResult.bm25_chunk_count}</span>
              </div>

              {rebuildResult.failed_documents.length > 0 && (
                <div className="mt-3 pt-3 border-t">
                  <span className="text-red-600 font-medium">失败文档：</span>
                  {rebuildResult.failed_documents.map((fd) => (
                    <div key={fd.doc_id} className="mt-1 text-xs text-red-500">
                      <span className="font-medium">{fd.filename}</span>: {fd.error}
                    </div>
                  ))}
                </div>
              )}

              {rebuildResult.warnings.length > 0 && (
                <div className="mt-2 pt-2 border-t">
                  {rebuildResult.warnings.map((w, i) => (
                    <div key={i} className="text-xs text-yellow-600">{w}</div>
                  ))}
                </div>
              )}
            </div>

            <button
              className="mt-4 w-full px-4 py-2 text-sm font-medium bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
              onClick={() => setRebuildResult(null)}
            >
              关闭
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
