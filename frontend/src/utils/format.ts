import { format, formatDistanceToNow, isToday, isYesterday } from "date-fns";
import type { User } from "@/types";

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
  if (isOnline) return "online";
  if (!dateStr) return "offline";
  return `last seen ${formatDistanceToNow(new Date(dateStr), { addSuffix: true })}`;
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
}): string {
  if (message.is_deleted) return "This message was deleted";
  switch (message.message_type) {
    case "image": return "📷 Photo";
    case "video": return "🎥 Video";
    case "pdf": return "📄 PDF";
    case "document": return "📎 Document";
    case "audio": return "🎵 Audio";
    default: return message.content || "";
  }
}
