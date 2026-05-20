import { useState, useRef, useEffect } from 'react';
import { Send, Square } from 'lucide-react';

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
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t border-gray-100 p-4">
      <div className="flex items-end gap-3 max-w-3xl mx-auto">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入您的问题..."
          rows={1}
          className="flex-1 resize-none border border-gray-200 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none max-h-32"
          disabled={isStreaming}
          onInput={(e) => {
            const el = e.currentTarget;
            el.style.height = 'auto';
            el.style.height = Math.min(el.scrollHeight, 128) + 'px';
          }}
        />
        {isStreaming ? (
          <button
            onClick={onCancel}
            className="flex-shrink-0 p-3 bg-red-500 text-white rounded-xl hover:bg-red-600 transition-colors"
          >
            <Square className="w-4 h-4" fill="currentColor" />
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={!input.trim()}
            className="flex-shrink-0 p-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}
