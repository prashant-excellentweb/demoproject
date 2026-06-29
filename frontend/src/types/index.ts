export interface User {
  id: number;
  phone_number: string;
  display_name: string;
  about: string;
  avatar?: string;
  avatar_url?: string | null;
  is_online: boolean;
  last_seen: string | null;
  date_joined?: string;
}

export interface Message {
  id: number;
  conversation: number;
  sender: User;
  message_type: "text" | "image" | "video" | "pdf" | "document" | "audio";
  content: string;
  file?: string;
  file_url?: string | null;
  file_name: string;
  file_size: number;
  is_read: boolean;
  created_at: string;
}

export interface Conversation {
  id: number;
  participants: User[];
  is_group: boolean;
  group_name: string;
  group_avatar_url?: string | null;
  last_message: Message | null;
  unread_count: number;
  created_at: string;
  updated_at: string;
}

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
