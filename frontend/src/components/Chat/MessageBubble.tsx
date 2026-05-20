import ReactMarkdown from 'react-markdown';
import { SourceCitation } from './SourceCitation';
import type { Message } from '../../types';

interface Props {
  message: Message;
  isStreaming: boolean;
}

export function MessageBubble({ message, isStreaming }: Props) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[80%] ${isUser ? 'order-1' : 'order-1'}`}>
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-800'
          }`}
        >
          {isUser ? (
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm max-w-none prose-p:my-1 prose-pre:my-1 prose-code:text-sm">
              <ReactMarkdown>{message.content || (isStreaming ? '思考中...' : '')}</ReactMarkdown>
              {isStreaming && (
                <span className="inline-block w-2 h-4 bg-gray-500 animate-pulse ml-0.5 align-middle" />
              )}
            </div>
          )}
        </div>
        {!isUser && message.sources && message.sources.length > 0 && (
          <SourceCitation sources={message.sources} />
        )}
      </div>
    </div>
  );
}
