import { DocumentManager } from '../Document/DocumentManager';
import { DocumentUploader } from '../Document/DocumentUploader';
import { DocumentList } from '../Document/DocumentList';
import { IndexStatusPanel } from '../Document/IndexStatusPanel';
import { useAppStore } from '../../store/appStore';
import { EmptyState } from '../shared/EmptyState';
import { SectionHeader } from '../shared/SectionHeader';
import { BookOpen, Upload, Plus } from 'lucide-react';
import { Card } from '../shared/Card';
import type { ViewType } from './AppLayout';

interface DocumentViewProps {
  onNavigate?: (view: ViewType) => void;
}

export function DocumentView({ onNavigate }: DocumentViewProps) {
  const { activeKnowledgeBaseId, knowledgeBases, setActiveKnowledgeBase } = useAppStore();

  if (!activeKnowledgeBaseId) {
    return (
      <div className="h-full overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 py-8">
          <SectionHeader
            title="文档管理"
            description="上传文档并管理索引状态"
          />
          <EmptyState
            icon={<BookOpen className="h-8 w-8" />}
            title="请先选择一个知识库"
            description="从下方知识库列表中选择一个，即可开始上传文档并构建索引"
            action={
              <div className="flex flex-col items-center gap-3">
                <div className="flex flex-wrap gap-2 justify-center">
                  {knowledgeBases.map((kb) => (
                    <button
                      key={kb.id}
                      onClick={() => setActiveKnowledgeBase(kb.id)}
                      className="px-4 py-2 text-sm font-medium text-brand-700 bg-brand-50 rounded-lg hover:bg-brand-100 transition-colors"
                    >
                      {kb.name}
                    </button>
                  ))}
                </div>
                {knowledgeBases.length === 0 && onNavigate && (
                  <button
                    onClick={() => onNavigate('knowledge-bases')}
                    className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-lg hover:bg-brand-700 transition-colors"
                  >
                    <Plus className="h-4 w-4" />
                    新建知识库
                  </button>
                )}
              </div>
            }
          />
        </div>
      </div>
    );
  }

  const activeKB = knowledgeBases.find((kb) => kb.id === activeKnowledgeBaseId);

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-4xl mx-auto px-6 py-8">
        <SectionHeader
          title={`文档管理${activeKB ? ` · ${activeKB.name}` : ''}`}
          description="上传文档、查看索引状态与管理操作"
        />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Upload + Docs */}
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <div className="flex items-center gap-2 mb-4">
                <Upload className="h-4 w-4 text-brand-600" />
                <h3 className="text-sm font-semibold text-text-primary">上传文档</h3>
              </div>
              <DocumentUploader />
            </Card>
            <Card>
              <h3 className="text-sm font-semibold text-text-primary mb-4">文档列表</h3>
              <DocumentList />
            </Card>
          </div>

          {/* Right: Index Status + Management */}
          <div className="space-y-6">
            <Card>
              <h3 className="text-sm font-semibold text-text-primary mb-3">索引状态</h3>
              <IndexStatusPanel />
            </Card>
            <Card>
              <h3 className="text-sm font-semibold text-text-primary mb-3">索引管理</h3>
              <p className="text-xs text-text-tertiary mb-3">
                重建索引将重新解析所有文档并重建向量和 BM25 索引
              </p>
              <DocumentManager />
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
