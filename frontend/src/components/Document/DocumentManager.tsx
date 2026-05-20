import { DocumentUploader } from './DocumentUploader';
import { DocumentList } from './DocumentList';

export function DocumentManager() {
  return (
    <div className="space-y-3">
      <span className="text-xs font-medium text-gray-500 uppercase tracking-wide px-2">文档</span>
      <DocumentUploader />
      <DocumentList />
    </div>
  );
}
