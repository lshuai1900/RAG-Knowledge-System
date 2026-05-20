import { useState, useRef, useCallback } from 'react';
import { Upload, Loader2 } from 'lucide-react';
import { uploadDocuments } from '../../api/document';
import { useAppStore } from '../../store/appStore';

const ALLOWED_TYPES = ['.pdf', '.txt', '.md', '.docx', '.doc'];

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
      setError('未选择支持的文件类型');
      return;
    }
    setError(null);
    setUploading(true);
    setIsUploading(true);
    try {
      await uploadDocuments(activeKnowledgeBaseId, fileArr);
      window.dispatchEvent(new CustomEvent('documents-changed'));
    } catch {
      setError('上传失败');
    } finally {
      setUploading(false);
      setIsUploading(false);
    }
  }, [activeKnowledgeBaseId, setIsUploading]);

  if (!activeKnowledgeBaseId) return null;

  return (
    <div
      className={`border-2 border-dashed rounded-lg p-4 text-center transition-colors cursor-pointer ${
        isDragging ? 'border-blue-400 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
      } ${uploading ? 'opacity-50 pointer-events-none' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(e) => { e.preventDefault(); setIsDragging(false); handleFiles(e.dataTransfer.files); }}
      onClick={() => fileInputRef.current?.click()}
    >
      <input
        ref={fileInputRef}
        type="file" multiple accept={ALLOWED_TYPES.join(',')}
        className="hidden" onChange={(e) => e.target.files && handleFiles(e.target.files)}
      />
      {uploading ? (
        <div className="flex items-center justify-center gap-2 text-sm text-blue-600">
          <Loader2 className="w-4 h-4 animate-spin" /> 上传中...
        </div>
      ) : (
        <>
          <Upload className="w-5 h-5 text-gray-400 mx-auto mb-2" />
          <p className="text-sm text-gray-500">拖拽文件到此处或点击上传</p>
          <p className="text-xs text-gray-400 mt-1">支持 PDF、TXT、MD、DOCX（最大 50MB）</p>
        </>
      )}
      {error && <p className="text-xs text-red-500 mt-2">{error}</p>}
    </div>
  );
}
