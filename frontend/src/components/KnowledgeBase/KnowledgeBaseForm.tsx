import { useState } from 'react';
import { X, BookOpen } from 'lucide-react';
import { createKnowledgeBase } from '../../api/knowledgeBase';
import { useAppStore } from '../../store/appStore';

interface Props {
  onClose: () => void;
  onCreated: () => void;
}

export function KnowledgeBaseForm({ onClose, onCreated }: Props) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const { setActiveKnowledgeBase } = useAppStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setError(null);
    setSubmitting(true);
    try {
      const kb = await createKnowledgeBase({ name: name.trim(), description: description.trim() });
      setActiveKnowledgeBase(kb.id);
      onCreated();
      onClose();
    } catch {
      setError('创建知识库失败，请稍后重试');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-elevated w-full max-w-md mx-4 p-6 animate-slide-up">
        <div className="flex items-center gap-3 mb-6">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
            <BookOpen className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-text-primary">新建知识库</h3>
            <p className="text-xs text-text-tertiary">创建后可上传文档并构建检索索引</p>
          </div>
          <button
            onClick={onClose}
            className="ml-auto p-2 rounded-lg text-text-tertiary hover:text-text-secondary hover:bg-surface-50 transition-colors"
            aria-label="关闭"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="kb-name" className="block text-sm font-medium text-text-primary mb-1.5">
              名称
            </label>
            <input
              id="kb-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full border border-surface-200 rounded-xl px-4 py-2.5 text-sm bg-surface-50 focus:bg-white focus:ring-2 focus:ring-brand-500/20 focus:border-brand-400 outline-none transition-all"
              placeholder="例如：论文研读、项目文档"
              autoFocus
            />
          </div>
          <div>
            <label htmlFor="kb-desc" className="block text-sm font-medium text-text-primary mb-1.5">
              描述 <span className="text-text-tertiary font-normal">（选填）</span>
            </label>
            <textarea
              id="kb-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full border border-surface-200 rounded-xl px-4 py-2.5 text-sm bg-surface-50 focus:bg-white focus:ring-2 focus:ring-brand-500/20 focus:border-brand-400 outline-none transition-all resize-none"
              rows={3}
              placeholder="简要描述知识库的用途..."
            />
          </div>
          {error && (
            <p className="text-sm text-red-500 bg-red-50 rounded-lg px-3 py-2">{error}</p>
          )}
          <div className="flex gap-3 justify-end pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 text-sm font-medium text-text-secondary hover:bg-surface-50 rounded-xl transition-colors"
              disabled={submitting}
            >
              取消
            </button>
            <button
              type="submit"
              disabled={!name.trim() || submitting}
              className="px-5 py-2.5 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed rounded-xl transition-colors shadow-sm"
            >
              {submitting ? '创建中...' : '创建知识库'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
