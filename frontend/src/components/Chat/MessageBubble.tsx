import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { SourceCitation } from './SourceCitation';
import { Bot, User } from 'lucide-react';
import type { Message } from '../../types';

interface Props {
  message: Message;
  isStreaming: boolean;
}

export function MessageBubble({ message, isStreaming }: Props) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="flex items-start gap-3 max-w-[80%] flex-row-reverse">
          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-brand-600 text-white">
            <User className="h-4 w-4" />
          </div>
          <div className="rounded-2xl rounded-tr-md px-4 py-3 bg-brand-600 text-white shadow-sm">
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="flex items-start gap-3 max-w-[85%]">
        <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-surface-100 text-text-secondary">
          <Bot className="h-4 w-4" />
        </div>
        <div className="min-w-0">
          <div className="rounded-2xl rounded-tl-md px-4 py-3 bg-white border border-surface-200 shadow-card">
            {message.content ? (
              <div className="prose-content text-sm">
                <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                  {message.content}
                </ReactMarkdown>
              </div>
            ) : isStreaming ? (
              <div className="flex items-center gap-2 text-text-tertiary text-sm">
                <span className="flex gap-1">
                  <span className="w-2 h-2 bg-brand-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 bg-brand-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 bg-brand-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </span>
                <span className="ml-1">检索知识库中...</span>
              </div>
            ) : null}
          </div>
          {!isUser && message.sources && message.sources.length > 0 && (
            <SourceCitation sources={message.sources} />
          )}
        </div>
      </div>
    </div>
  );
}
