import { useState, useRef, useCallback } from 'react';
import axios from 'axios';
import { Upload, Loader2, FileUp } from 'lucide-react';
import { uploadDocuments } from '../../api/document';
import { useAppStore } from '../../store/appStore';

const ALLOWED_TYPES = ['.pdf', '.txt', '.md', '.docx', '.doc'];
const ALLOWED_LABELS = ['PDF', 'TXT', 'MD', 'DOCX', 'DOC'];

export function DocumentUploader() {
  const { activeKnowledgeBaseId, setIsUploading } = useAppStore();
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(async (files: FileList) => {
    if (!activeKnowledgeBaseId) return;
    const fileArr = Array.from(files).filter((f) =>
      ALLOWED_TYPES.some((ext) => f.name.toLowerCase().endsWith(ext))
    );
    if (fileArr.length === 0) {
      setError(`请上传支持的文件类型：${ALLOWED_LABELS.join('、')}`);
      return;
    }
    setError(null);
    setUploading(true);
    setIsUploading(true);
    try {
      await uploadDocuments(activeKnowledgeBaseId, fileArr);
      window.dispatchEvent(new CustomEvent('documents-changed'));
    } catch (err) {
      const detail = axios.isAxiosError(err) ? err.response?.data?.detail : null;
      setError(detail?.message || '上传失败，请重试');
    } finally {
      setUploading(false);
      setIsUploading(false);
    }
  }, [activeKnowledgeBaseId, setIsUploading]);

  const handleClick = () => {
    if (!uploading) fileInputRef.current?.click();
  };

  return (
    <div>
      <div
        className={`relative border-2 border-dashed rounded-2xl p-8 text-center transition-all cursor-pointer ${
          isDragging
            ? 'border-brand-400 bg-brand-50/50 scale-[1.02]'
            : uploading
              ? 'border-brand-200 bg-brand-50/30'
              : 'border-surface-200 hover:border-brand-200 hover:bg-surface-50'
        }`}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => { e.preventDefault(); setIsDragging(false); handleFiles(e.dataTransfer.files); }}
        onClick={handleClick}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter') handleClick(); }}
        aria-label="上传文档"
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ALLOWED_TYPES.join(',')}
          className="hidden"
          onChange={(e) => e.target.files && handleFiles(e.target.files)}
        />

        {uploading ? (
          <div className="flex flex-col items-center gap-2">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-100">
              <Loader2 className="h-6 w-6 text-brand-600 animate-spin" />
            </div>
            <p className="text-sm font-medium text-brand-700">正在上传文档...</p>
            <p className="text-xs text-text-tertiary">文件将自动解析并建立索引</p>
          </div>
        ) : (
          <>
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-surface-100 mx-auto mb-3">
              <FileUp className="h-6 w-6 text-text-tertiary" />
            </div>
            <p className="text-sm font-medium text-text-secondary">
              拖拽文件到此处或<span className="text-brand-600">点击上传</span>
            </p>
            <p className="text-xs text-text-tertiary mt-1.5">
              支持 {ALLOWED_LABELS.join('、')} 格式，单个文件最大 50MB
            </p>
          </>
        )}
      </div>

      {error && (
        <div className="mt-3 flex items-center gap-2 text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2">
          <Upload className="h-3.5 w-3.5 flex-shrink-0" />
          {error}
          <button
            className="ml-auto text-red-500 hover:underline flex-shrink-0"
            onClick={() => setError(null)}
          >
            关闭
          </button>
        </div>
      )}
    </div>
  );
}
