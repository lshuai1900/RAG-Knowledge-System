import { useEffect, useRef } from 'react';
import { useAppStore } from '../../store/appStore';
import { MessageBubble } from './MessageBubble';
import { Cpu } from 'lucide-react';

export function MessageList() {
  const messages = useAppStore((s) => s.messages);
  const isStreaming = useAppStore((s) => s.isStreaming);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto px-4 py-6 space-y-5">
        {messages.map((msg, i) => {
          const isLast = i === messages.length - 1;
          const isAssistant = msg.role === 'assistant';
          return (
            <div key={msg.id} className="animate-fade-in">
              <MessageBubble
                message={msg}
                isStreaming={isStreaming && isLast && isAssistant}
              />
              {/* Streaming indicator */}
              {isStreaming && isLast && isAssistant && msg.content && (
                <div className="flex items-center gap-2 mt-2 ml-1 text-xs text-text-tertiary animate-pulse-soft">
                  <Cpu className="h-3 w-3" />
                  正在生成...
                </div>
              )}
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
