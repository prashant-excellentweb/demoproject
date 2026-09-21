import { format, formatDistanceToNow, isToday, isYesterday } from "date-fns";
import type { Conversation, Message, MessageQuote, MessageSearchHit, User } from "@/types";

export function formatMessageTime(dateStr: string): string {
  const date = new Date(dateStr);
  if (isToday(date)) return format(date, "HH:mm");
  if (isYesterday(date)) return "Yesterday";
  return format(date, "dd/MM/yyyy");
}

export function formatChatTime(dateStr: string): string {
  const date = new Date(dateStr);
  if (isToday(date)) return format(date, "HH:mm");
  if (isYesterday(date)) return "Yesterday";
  return format(date, "dd/MM/yy");
}

export function formatLastSeen(dateStr: string | null, isOnline: boolean): string {
  // Backend redacts last_seen + is_online when privacy hides them (both null/false).
  if (!dateStr && !isOnline) return "";
  if (isOnline) return "online";
  return `last seen ${formatDistanceToNow(new Date(dateStr!), { addSuffix: true })}`;
}

export function getInitials(user: User): string {
  const name = user.display_name || user.phone_number;
  return name.slice(0, 2).toUpperCase();
}

export function getDisplayName(user: User): string {
  return user.display_name || user.phone_number;
}

export function getOtherParticipant(conversation: { participants: User[] }, currentUserId: number): User | undefined {
  return conversation.participants.find((p) => p.id !== currentUserId);
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function getMessagePreview(message: {
  message_type: string;
  content: string;
  file_name?: string;
  is_deleted?: boolean;
  is_view_once?: boolean;
  view_once_opened?: boolean;
}): string {
  if (message.is_deleted) return "This message was deleted";
  if (message.is_view_once) {
    if (message.view_once_opened) {
      return message.message_type === "video" ? "Opened view once video" : "Opened view once photo";
    }
    return message.message_type === "video" ? "View once video" : "View once photo";
  }
  switch (message.message_type) {
    case "image": return "📷 Photo";
    case "video": return "🎥 Video";
    case "pdf": return "📄 PDF";
    case "document": return "📎 Document";
    case "audio": return "🎵 Audio";
    default: return message.content || "";
  }
}

export function toMessageQuote(message: Message): MessageQuote {
  return {
    id: message.id,
    sender_id: message.sender.id,
    sender_name: getDisplayName(message.sender),
    message_type: message.message_type,
    content: (message.content || "").slice(0, 120),
    file_name: message.file_name || "",
    is_deleted: Boolean(message.is_deleted),
  };
}

export function getQuotePreview(quote: MessageQuote): string {
  return getMessagePreview(quote);
}

/** Matches backend MESSAGE_EDIT_WINDOW_MINUTES (default 15). */
export const MESSAGE_EDIT_WINDOW_MS = 15 * 60 * 1000;

export function canEditMessage(message: Message, isSent: boolean, now = Date.now()): boolean {
  if (!isSent || message.is_deleted) return false;
  if (message.message_type !== "text") return false;
  const created = new Date(message.created_at).getTime();
  if (Number.isNaN(created)) return false;
  return now - created < MESSAGE_EDIT_WINDOW_MS;
}

export function conversationFromSearchHit(hit: MessageSearchHit): Conversation {
  return {
    id: hit.chat.id,
    participants: hit.chat.participants,
    is_group: hit.chat.is_group,
    group_name: hit.chat.group_name,
    group_avatar_url: hit.chat.group_avatar_url,
    last_message: null,
    unread_count: 0,
    created_at: hit.created_at,
    updated_at: hit.created_at,
  };
}
