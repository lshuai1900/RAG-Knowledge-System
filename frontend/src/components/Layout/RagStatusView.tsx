import { RagEngineStatusPanel } from '../Document/RagEngineStatusPanel';
import { IndexStatusPanel } from '../Document/IndexStatusPanel';
import { useAppStore } from '../../store/appStore';
import { SectionHeader } from '../shared/SectionHeader';
import { Card } from '../shared/Card';

export function RagStatusView() {
  const { activeKnowledgeBaseId } = useAppStore();

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-4xl mx-auto px-6 py-8">
        <SectionHeader
          title="RAG 引擎状态"
          description="查看当前 RAG 引擎配置、检索流程与系统状态"
        />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <RagEngineStatusPanel />
          {activeKnowledgeBaseId && (
            <Card>
              <h3 className="text-sm font-semibold text-text-primary mb-3">当前知识库索引</h3>
              <IndexStatusPanel />
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
