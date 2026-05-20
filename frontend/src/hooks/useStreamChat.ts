import { useRef, useCallback } from 'react';
import { useAppStore } from '../store/appStore';

interface UseStreamChatReturn {
  streamQuery: (kbId: string, sessionId: string, query: string) => Promise<void>;
  cancelStream: () => void;
}

export function useStreamChat(): UseStreamChatReturn {
  const { addMessage, updateLastAssistantMessage, setStreaming } = useAppStore();
  const abortRef = useRef<AbortController | null>(null);

  const streamQuery = useCallback(async (kbId: string, sessionId: string, query: string) => {
    const abortController = new AbortController();
    abortRef.current = abortController;

    const tempId = `temp_${Date.now()}`;

    addMessage({ id: tempId, role: 'assistant', content: '', created_at: new Date().toISOString() });
    setStreaming(true);

    try {
      const response = await fetch('/api/v1/chat/query/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kb_id: kbId, session_id: sessionId, query }),
        signal: abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let currentEvent = '';
      let content = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (currentEvent === 'chunk') {
                content += data.text;
                updateLastAssistantMessage(content);
              } else if (currentEvent === 'sources') {
                // Update sources on the streaming message
                const msgs = useAppStore.getState().messages;
                const idx = msgs.findIndex((m) => m.id === tempId);
                if (idx >= 0) {
                  msgs[idx] = { ...msgs[idx], sources: data.sources };
                  useAppStore.setState({ messages: [...msgs] });
                }
              } else if (currentEvent === 'done') {
                // Update temp message with real ID
                const msgs = useAppStore.getState().messages;
                const idx = msgs.findIndex((m) => m.id === tempId);
                if (idx >= 0) {
                  msgs[idx] = { ...msgs[idx], id: data.message_id };
                  useAppStore.setState({ messages: [...msgs] });
                }
              }
            } catch {
              // skip parse errors on partial data
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') return;
      updateLastAssistantMessage('错误：获取回复失败，请重试');
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  }, [addMessage, updateLastAssistantMessage, setStreaming]);

  const cancelStream = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return { streamQuery, cancelStream };
}
