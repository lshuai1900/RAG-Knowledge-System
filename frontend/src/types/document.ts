export interface Document {
  id: string;
  kb_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: 'pending' | 'processing' | 'ready' | 'failed';
  error_message?: string;
  chunk_count: number;
  created_at: string;
}
