import type { Conversation } from "@/types";

export function isGroupAdmin(conversation: Conversation, currentUserId: number): boolean {
  if (!conversation.is_group) return false;
  if (conversation.is_admin === true) return true;
  if (conversation.created_by != null) {
    return conversation.created_by === currentUserId;
  }
  if (conversation.participants.length === 0) return false;
  const fallbackAdminId = Math.min(...conversation.participants.map((p) => p.id));
  return fallbackAdminId === currentUserId;
}
