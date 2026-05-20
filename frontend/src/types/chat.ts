export interface ChatSession {
  id: string;
  kb_id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  created_at: string;
}

export interface Source {
  content: string;
  document_name: string;
  chunk_index: number;
  score: number;
}

export interface StreamChunk {
  text: string;
}
