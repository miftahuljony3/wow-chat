"use client";

import { useEffect, useCallback } from "react";
import { useInboxStore } from "@/hooks/useStore";
import { inboxApi } from "@/lib/api";
import { useInboxWebSocket } from "@/hooks/useWebSocket";
import ConversationList from "@/components/ConversationList";
import ChatWindow from "@/components/ChatWindow";
import Sidebar from "@/components/Sidebar";
import { Search } from "lucide-react";

export default function DashboardPage() {
  const { conversations, activeConversationId, setConversations,
          setActiveConversation, addMessage, upsertConversation, updateConversation } = useInboxStore();

  // Load conversation list on mount
  useEffect(() => {
    inboxApi.conversations().then((res) => {
      setConversations(res.data.results ?? []);
    });
  }, [setConversations]);

  // Handle incoming WebSocket messages
  const handleWsMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const { type, data } = JSON.parse(event.data);

        if (type === "new_message") {
          addMessage(data.message);
          upsertConversation({
            ...data.conversation,
            last_message_preview: data.message.content,
            last_message_at: data.message.created_at,
          });
        }

        if (type === "conversation_update") {
          updateConversation(data.conversation_id, data);
        }
      } catch {
        // ignore malformed frames
      }
    },
    [addMessage, upsertConversation, updateConversation]
  );

  useInboxWebSocket(handleWsMessage);

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <Sidebar />

      {/* Conversation list panel */}
      <div className="w-80 flex flex-col border-r border-border bg-white">
        {/* Header */}
        <div className="px-4 py-4 border-b border-border">
          <h1 className="font-semibold text-base">Unified Inbox</h1>
          <p className="text-xs text-muted-foreground mt-0.5">All channels in one place</p>
        </div>

        {/* Search */}
        <div className="px-3 py-2 border-b border-border">
          <div className="flex items-center gap-2 bg-muted rounded-lg px-3 py-1.5">
            <Search size={14} className="text-muted-foreground" />
            <input
              className="bg-transparent text-sm flex-1 focus:outline-none placeholder:text-muted-foreground"
              placeholder="Search conversations..."
            />
          </div>
        </div>

        {/* List */}
        <div className="flex-1 overflow-hidden">
          <ConversationList
            conversations={conversations}
            onSelect={setActiveConversation}
          />
        </div>
      </div>

      {/* Chat panel */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {activeConversationId ? (
          <ChatWindow conversationId={activeConversationId} />
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center gap-3 text-muted-foreground">
            <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center">
              <span className="text-3xl">💬</span>
            </div>
            <div>
              <p className="font-medium text-foreground">Wow Chat</p>
              <p className="text-sm">Select a conversation to start messaging</p>
              <p className="text-xs mt-1 text-primary/70">An intelligent assistant by JONY</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
