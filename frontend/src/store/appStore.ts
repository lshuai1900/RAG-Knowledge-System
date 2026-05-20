import { create } from 'zustand';
import type { KnowledgeBase, Document, ChatSession, Message } from '../types';

interface AppState {
  knowledgeBases: KnowledgeBase[];
  activeKnowledgeBaseId: string | null;
  isLoadingKBs: boolean;

  documents: Document[];
  isUploading: boolean;

  chatSessions: ChatSession[];
  activeSessionId: string | null;
  messages: Message[];
  isStreaming: boolean;

  setKnowledgeBases: (kbs: KnowledgeBase[]) => void;
  setActiveKnowledgeBase: (id: string | null) => void;
  setIsLoadingKBs: (v: boolean) => void;

  setDocuments: (docs: Document[]) => void;
  setIsUploading: (v: boolean) => void;

  setChatSessions: (sessions: ChatSession[]) => void;
  setActiveSession: (id: string | null) => void;
  addMessage: (msg: Message) => void;
  updateLastAssistantMessage: (content: string) => void;
  setMessages: (msgs: Message[]) => void;
  setStreaming: (v: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  knowledgeBases: [],
  activeKnowledgeBaseId: null,
  isLoadingKBs: false,

  documents: [],
  isUploading: false,

  chatSessions: [],
  activeSessionId: null,
  messages: [],
  isStreaming: false,

  setKnowledgeBases: (kbs) => set({ knowledgeBases: kbs }),
  setActiveKnowledgeBase: (id) => set({ activeKnowledgeBaseId: id, activeSessionId: null, messages: [] }),
  setIsLoadingKBs: (v) => set({ isLoadingKBs: v }),

  setDocuments: (docs) => set({ documents: docs }),
  setIsUploading: (v) => set({ isUploading: v }),

  setChatSessions: (sessions) => set({ chatSessions: sessions }),
  setActiveSession: (id) => set({ activeSessionId: id }),
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  updateLastAssistantMessage: (content) =>
    set((s) => {
      const msgs = [...s.messages];
      let lastIdx = msgs.length - 1;
      while (lastIdx >= 0 && msgs[lastIdx].role !== 'assistant') lastIdx--;
      if (lastIdx >= 0) {
        msgs[lastIdx] = { ...msgs[lastIdx], content };
      }
      return { messages: msgs };
    }),
  setMessages: (msgs) => set({ messages: msgs }),
  setStreaming: (v) => set({ isStreaming: v }),
}));
