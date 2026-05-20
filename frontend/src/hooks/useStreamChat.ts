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
      const apiBase = import.meta.env.VITE_API_BASE_URL || '/api/v1';
      const response = await fetch(`${apiBase}/chat/query/stream`, {
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
      let content = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE events are delimited by double newlines
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';

        for (const part of parts) {
          if (!part.trim()) continue;
          let eventType = '';
          let dataStr = '';

          for (const line of part.split('\n')) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith('data: ')) {
              dataStr += line.slice(6);
            }
          }

          if (!dataStr) continue;

          try {
            const data = JSON.parse(dataStr);
            if (eventType === 'chunk') {
              content += data.text;
              updateLastAssistantMessage(content);
            } else if (eventType === 'sources') {
              const msgs = useAppStore.getState().messages;
              const idx = msgs.findIndex((m) => m.id === tempId);
              if (idx >= 0) {
                msgs[idx] = { ...msgs[idx], sources: data.sources };
                useAppStore.setState({ messages: [...msgs] });
              }
            } else if (eventType === 'done') {
              const msgs = useAppStore.getState().messages;
              const idx = msgs.findIndex((m) => m.id === tempId);
              if (idx >= 0) {
                msgs[idx] = { ...msgs[idx], id: data.message_id };
                useAppStore.setState({ messages: [...msgs] });
              }
            }
          } catch {
            // skip parse errors on malformed data
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') {
        useAppStore.setState((s) => ({ messages: s.messages.filter((m) => m.id !== tempId) }));
        return;
      }
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
