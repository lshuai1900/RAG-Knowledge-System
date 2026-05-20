import { useEffect, useRef } from 'react';
import { useAppStore } from '../../store/appStore';
import { MessageBubble } from './MessageBubble';

export function MessageList() {
  const { messages, isStreaming } = useAppStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-gray-400">输入问题开始对话</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} isStreaming={isStreaming && msg.id.startsWith('temp_')} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
