"use client";

import { useInboxStore, Conversation } from "@/hooks/useStore";
import { cn, timeAgo, getInitials } from "@/lib/utils";
import { MessageSquare, Bot } from "lucide-react";

interface Props {
  conversations: Conversation[];
  onSelect: (id: string) => void;
}

function PlatformBadge({ platform }: { platform: string }) {
  if (platform === "whatsapp")
    return (
      <span className="text-[10px] font-semibold text-green-600 bg-green-50 px-1.5 py-0.5 rounded-full">
        WA
      </span>
    );
  return (
    <span className="text-[10px] font-semibold text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded-full">
      FB
    </span>
  );
}

export default function ConversationList({ conversations, onSelect }: Props) {
  const activeId = useInboxStore((s) => s.activeConversationId);

  if (conversations.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-2 p-8 text-center">
        <MessageSquare size={40} className="opacity-30" />
        <p className="text-sm">No conversations yet. Connect a WhatsApp channel to get started.</p>
      </div>
    );
  }

  return (
    <ul className="overflow-y-auto h-full chat-scroll">
      {conversations.map((conv) => (
        <li key={conv.id}>
          <button
            onClick={() => onSelect(conv.id)}
            className={cn(
              "w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-muted/50 transition-colors border-b border-border/50",
              activeId === conv.id && "bg-primary/5 border-l-2 border-l-primary"
            )}
          >
            {/* Avatar */}
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary/80 to-primary flex-shrink-0 flex items-center justify-center text-white text-sm font-semibold">
              {getInitials(conv.contact_name)}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-1">
                <span className="font-medium text-sm truncate">{conv.contact_name}</span>
                <span className="text-[11px] text-muted-foreground flex-shrink-0">
                  {timeAgo(conv.last_message_at)}
                </span>
              </div>
              <div className="flex items-center gap-1 mt-0.5">
                <PlatformBadge platform={conv.platform} />
                <p className="text-xs text-muted-foreground truncate flex-1">
                  {conv.last_message_preview}
                </p>
                {conv.unread_count > 0 && (
                  <span className="text-[10px] bg-primary text-white rounded-full w-4 h-4 flex items-center justify-center flex-shrink-0">
                    {conv.unread_count > 9 ? "9+" : conv.unread_count}
                  </span>
                )}
              </div>
              {!conv.bot_active && (
                <span className="text-[10px] text-amber-600 flex items-center gap-0.5 mt-0.5">
                  <Bot size={10} /> Human mode
                </span>
              )}
            </div>
          </button>
        </li>
      ))}
    </ul>
  );
}
