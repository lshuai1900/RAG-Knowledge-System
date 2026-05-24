import { useState, useRef, useEffect } from 'react';
import { Send, Square, Loader2 } from 'lucide-react';

interface Props {
  onSend: (query: string) => void;
  onCancel: () => void;
  isStreaming: boolean;
}

export function ChatInput({ onSend, onCancel, isStreaming }: Props) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!isStreaming) {
      textareaRef.current?.focus();
    }
  }, [isStreaming]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;
    onSend(trimmed);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex-shrink-0 border-t border-surface-100 bg-white px-4 py-4">
      <div className="flex items-end gap-3 max-w-3xl mx-auto">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isStreaming ? '正在生成回答...' : '输入您的问题，Enter 发送，Shift+Enter 换行'}
            rows={1}
            className="w-full resize-none border border-surface-200 rounded-2xl px-4 py-3 pr-10 text-sm leading-5 bg-surface-50 placeholder:text-text-tertiary focus:bg-white focus:ring-2 focus:ring-brand-500/20 focus:border-brand-400 outline-none transition-all max-h-36"
            disabled={isStreaming}
            onInput={(e) => {
              const el = e.currentTarget;
              el.style.height = 'auto';
              el.style.height = Math.min(el.scrollHeight, 144) + 'px';
            }}
            aria-label="输入问题"
          />
          {isStreaming && (
            <div className="absolute right-3 bottom-3">
              <Loader2 className="h-4 w-4 text-brand-500 animate-spin" />
            </div>
          )}
        </div>
        {isStreaming ? (
          <button
            onClick={onCancel}
            className="flex-shrink-0 p-3 bg-red-500 text-white rounded-2xl hover:bg-red-600 transition-all shadow-sm hover:shadow-md"
            aria-label="停止生成"
          >
            <Square className="w-4 h-4" fill="currentColor" />
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={!input.trim()}
            className="flex-shrink-0 p-3 bg-brand-600 text-white rounded-2xl hover:bg-brand-700 disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-sm hover:shadow-md"
            aria-label="发送消息"
          >
            <Send className="w-4 h-4" />
          </button>
        )}
      </div>
      <p className="text-center text-[10px] text-text-tertiary mt-2">
        RAG 检索增强生成 · 回答基于知识库文档内容
      </p>
    </div>
  );
}
