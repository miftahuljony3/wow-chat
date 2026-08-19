"use client";

import { useState, useRef, useEffect } from "react";
import { useInboxStore, Message } from "@/hooks/useStore";
import { cn, timeAgo, getInitials } from "@/lib/utils";
import { Send, Bot, User, BotOff } from "lucide-react";
import { aiApi, inboxApi } from "@/lib/api";

interface Props {
  conversationId: string;
}

function MessageBubble({ msg }: { msg: Message }) {
  const isOutbound = msg.direction === "outbound";
  return (
    <div className={cn("flex gap-2 max-w-[75%]", isOutbound ? "ml-auto flex-row-reverse" : "")}>
      {/* Avatar */}
      <div
        className={cn(
          "w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-semibold text-white mt-1",
          isOutbound ? "bg-primary" : "bg-slate-500"
        )}
      >
        {isOutbound ? <Bot size={14} /> : getInitials(msg.sender_name)}
      </div>

      {/* Bubble */}
      <div
        className={cn(
          "rounded-2xl px-3 py-2 text-sm leading-relaxed shadow-sm",
          isOutbound
            ? "bg-primary text-white rounded-tr-sm"
            : "bg-white border border-border rounded-tl-sm"
        )}
      >
        <p className="whitespace-pre-wrap break-words">{msg.content}</p>
        <p
          className={cn(
            "text-[10px] mt-1",
            isOutbound ? "text-white/60 text-right" : "text-muted-foreground"
          )}
        >
          {timeAgo(msg.created_at)}
        </p>
      </div>
    </div>
  );
}

export default function ChatWindow({ conversationId }: Props) {
  const conversation = useInboxStore((s) =>
    s.conversations.find((c) => c.id === conversationId)
  );
  const messages = useInboxStore((s) => s.messagesByConversation[conversationId] ?? []);
  const { setMessages, updateConversation } = useInboxStore();

  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    inboxApi.messages(conversationId).then((res) => {
      const msgs: Message[] = (res.data.results ?? []).reverse();
      setMessages(conversationId, msgs);
    });
    inboxApi.markRead(conversationId).catch(() => null);
  }, [conversationId, setMessages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || sending) return;
    setSending(true);
    try {
      // TODO: call outbound send API (Phase 6 outbound endpoint)
      console.log("Send:", input);
      setInput("");
    } finally {
      setSending(false);
    }
  };

  const toggleBot = async () => {
    if (!conversation) return;
    const next = !conversation.bot_active;
    updateConversation(conversationId, { bot_active: next });
    await aiApi.toggleBot(conversationId, next);
  };

  if (!conversation) return null;

  return (
    <div className="flex flex-col h-full bg-[#f0f2f5]">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-white border-b border-border shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary/80 to-primary flex items-center justify-center text-white text-sm font-semibold">
            {getInitials(conversation.contact_name)}
          </div>
          <div>
            <p className="font-semibold text-sm">{conversation.contact_name}</p>
            <p className="text-xs text-muted-foreground capitalize">{conversation.platform}</p>
          </div>
        </div>

        {/* Bot toggle */}
        <button
          onClick={toggleBot}
          title={conversation.bot_active ? "Disable AI bot" : "Enable AI bot"}
          className={cn(
            "flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full font-medium transition-colors",
            conversation.bot_active
              ? "bg-primary/10 text-primary hover:bg-primary/20"
              : "bg-amber-100 text-amber-700 hover:bg-amber-200"
          )}
        >
          {conversation.bot_active ? <Bot size={13} /> : <BotOff size={13} />}
          {conversation.bot_active ? "AI Active" : "Human Mode"}
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto chat-scroll p-4 flex flex-col gap-3">
        {messages.length === 0 && (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-sm text-muted-foreground">No messages yet.</p>
          </div>
        )}
        {messages.map((msg) => (
          <MessageBubble key={msg.id} msg={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="flex items-center gap-2 px-4 py-3 bg-white border-t border-border">
        <input
          className="flex-1 rounded-full border border-border px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
          placeholder="Type a message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || sending}
          className="w-9 h-9 rounded-full bg-primary text-white flex items-center justify-center disabled:opacity-50 hover:bg-primary/90 transition-colors"
        >
          <Send size={15} />
        </button>
      </div>
    </div>
  );
}
