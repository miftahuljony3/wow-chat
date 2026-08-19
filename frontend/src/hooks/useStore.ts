import { create } from "zustand";

export interface Message {
  id: string;
  conversation_id: string;
  direction: "inbound" | "outbound";
  sender_name: string;
  message_type: string;
  content: string;
  created_at: string;
  is_read: boolean;
}

export interface Conversation {
  id: string;
  platform: string;
  contact_id: string;
  contact_name: string;
  bot_active: boolean;
  status: string;
  last_message_at: string;
  last_message_preview: string;
  unread_count: number;
  assigned_agent_id: string | null;
}

interface InboxStore {
  conversations: Conversation[];
  activeConversationId: string | null;
  messagesByConversation: Record<string, Message[]>;

  setConversations: (convs: Conversation[]) => void;
  setActiveConversation: (id: string) => void;
  setMessages: (conversationId: string, msgs: Message[]) => void;
  addMessage: (msg: Message) => void;
  updateConversation: (id: string, data: Partial<Conversation>) => void;
  upsertConversation: (conv: Conversation) => void;
}

export const useInboxStore = create<InboxStore>((set) => ({
  conversations: [],
  activeConversationId: null,
  messagesByConversation: {},

  setConversations: (convs) => set({ conversations: convs }),

  setActiveConversation: (id) => set({ activeConversationId: id }),

  setMessages: (conversationId, msgs) =>
    set((state) => ({
      messagesByConversation: {
        ...state.messagesByConversation,
        [conversationId]: msgs,
      },
    })),

  addMessage: (msg) =>
    set((state) => {
      const existing = state.messagesByConversation[msg.conversation_id] ?? [];
      const alreadyExists = existing.some((m) => m.id === msg.id);
      if (alreadyExists) return state;
      return {
        messagesByConversation: {
          ...state.messagesByConversation,
          [msg.conversation_id]: [...existing, msg],
        },
      };
    }),

  updateConversation: (id, data) =>
    set((state) => ({
      conversations: state.conversations.map((c) =>
        c.id === id ? { ...c, ...data } : c
      ),
    })),

  upsertConversation: (conv) =>
    set((state) => {
      const idx = state.conversations.findIndex((c) => c.id === conv.id);
      if (idx >= 0) {
        const updated = [...state.conversations];
        updated[idx] = { ...updated[idx], ...conv };
        return { conversations: updated };
      }
      return { conversations: [conv, ...state.conversations] };
    }),
}));

interface AuthStore {
  user: Record<string, unknown> | null;
  token: string | null;
  setAuth: (user: Record<string, unknown>, token: string, refresh: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  token: null,
  setAuth: (user, token, refresh) => {
    localStorage.setItem("access_token", token);
    localStorage.setItem("refresh_token", refresh);
    set({ user, token });
  },
  logout: () => {
    localStorage.clear();
    set({ user: null, token: null });
  },
}));
