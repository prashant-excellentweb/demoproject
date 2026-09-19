/** WhatsApp-style audience for profile fields and status. */
export type PrivacyVisibility = "everyone" | "contacts" | "nobody";

export interface PrivacySettings {
  profile_photo_privacy: PrivacyVisibility;
  about_privacy: PrivacyVisibility;
  last_seen_privacy: PrivacyVisibility;
  status_privacy: PrivacyVisibility;
}

export interface User {
  id: number;
  phone_number: string;
  display_name: string;
  about: string;
  avatar?: string;
  avatar_url?: string | null;
  is_online: boolean;
  last_seen: string | null;
  profile_setup_complete?: boolean;
  date_joined?: string;
  /** Who can see profile photo: everyone | contacts | nobody */
  profile_photo_privacy?: PrivacyVisibility;
  /** Who can see about text */
  about_privacy?: PrivacyVisibility;
  /** Who can see online / last seen */
  last_seen_privacy?: PrivacyVisibility;
  /** Who can see status / stories */
  status_privacy?: PrivacyVisibility;
}

export interface MessageReactionSummary {
  emoji: string;
  count: number;
  user_ids: number[];
}

export type MessageType = "text" | "image" | "video" | "pdf" | "document" | "audio";

/** Nested quote shown above an inline reply (and on drafts). */
export interface MessageQuote {
  id: number;
  sender_id: number;
  sender_name: string;
  message_type: MessageType;
  content: string;
  file_name: string;
  is_deleted: boolean;
}

export interface MessageDraft {
  conversation: number;
  content: string;
  reply_to: MessageQuote | null;
  updated_at: string;
}

export interface Message {
  id: number;
  conversation: number;
  sender: User;
  message_type: MessageType;
  content: string;
  file?: string;
  file_url?: string | null;
  file_name: string;
  file_size: number;
  reply_to?: MessageQuote | null;
  is_forwarded?: boolean;
  forwarded_from?: number | null;
  is_edited?: boolean;
  edited_at?: string | null;
  is_read: boolean;
  is_deleted?: boolean;
  deleted_at?: string | null;
  reactions?: MessageReactionSummary[];
  my_reaction?: string | null;
  created_at: string;
}

export interface ConversationSearchSummary {
  id: number;
  is_group: boolean;
  group_name: string;
  group_avatar_url?: string | null;
  participants: User[];
  name: string;
}

export interface MessageSearchHit {
  id: number;
  conversation: number;
  sender: User;
  message_type: MessageType;
  content: string;
  file_name: string;
  snippet: string;
  created_at: string;
  chat: ConversationSearchSummary;
}

export interface MessageSearchResponse {
  query: string;
  results: MessageSearchHit[];
  has_more: boolean;
}

export interface ForwardResult {
  forwarded: Message[];
  failed: { conversation_id: number; error: string }[];
}

export interface Conversation {
  id: number;
  participants: User[];
  is_group: boolean;
  group_name: string;
  group_avatar_url?: string | null;
  created_by?: number | null;
  is_admin?: boolean;
  is_favourite?: boolean;
  is_archived?: boolean;
  is_blocked?: boolean;
  is_pinned?: boolean;
  last_message: Message | null;
  draft?: MessageDraft | null;
  unread_count: number;
  created_at: string;
  updated_at: string;
}

export type ChatListFilter = "all" | "unread" | "groups" | "favourites" | "archived" | "blocked";

export interface Status {
  id: number;
  user: User;
  status_type: "text" | "image" | "video";
  content: string;
  media_url?: string | null;
  background_color: string;
  created_at: string;
  expires_at: string;
  is_viewed: boolean;
  view_count: number;
}

export interface StatusGroup {
  user: User;
  statuses: Status[];
  has_unviewed: boolean;
  latest_at: string;
}

export interface StatusFeed {
  my_statuses: Status[];
  contacts: StatusGroup[];
}

export interface AuthResponse {
  access: string;
  refresh: string;
  user: User;
  is_new_user: boolean;
}
