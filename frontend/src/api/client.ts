import axios, { type AxiosResponse } from "axios";
import type { Conversation, ChatListFilter, Message, Status, StatusFeed, User } from "@/types";

const API_BASE = import.meta.env.VITE_API_URL || "/api";

export interface ApiResponse<T = unknown> {
  success: boolean;
  message: string;
  data: T;
}

export interface AxiosApiResponse<T = unknown> extends AxiosResponse<T> {
  apiSuccess?: boolean;
  apiMessage?: string;
}

const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

function unwrapResponse<T>(res: AxiosResponse): AxiosApiResponse<T> {
  const body = res.data as ApiResponse<T> | T;
  if (body && typeof body === "object" && "success" in body && "message" in body && "data" in body) {
    const wrapped = body as ApiResponse<T>;
    const unwrapped = res as AxiosApiResponse<T>;
    unwrapped.apiSuccess = wrapped.success;
    unwrapped.apiMessage = wrapped.message;
    unwrapped.data = wrapped.data as T;
  }
  return res as AxiosApiResponse<T>;
}

api.interceptors.response.use(
  (res) => unwrapResponse(res),
  (err) => {
    const body = err.response?.data as ApiResponse | { detail?: string } | undefined;
    if (body && typeof body === "object" && "success" in body && "message" in body) {
      err.message = (body as ApiResponse).message;
    } else if (body && typeof body === "object" && "detail" in body) {
      err.message = String(body.detail);
    }
    if (err.response?.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export interface AuthTokenData {
  access: string;
  refresh: string;
  user: User;
  is_new_user: boolean;
  requires_profile_setup: boolean;
}

export const authApi = {
  sendOtp: (phone_number: string) =>
    api.post<{ phone_number: string }>("/auth/send-otp/", { phone_number }),
  verifyOtp: (phone_number: string, otp_code: string) =>
    api.post<AuthTokenData>("/auth/verify-otp/", { phone_number, otp_code }),
  getProfile: () => api.get<User>("/auth/profile/"),
  updateProfile: (data: FormData) =>
    api.patch<User>("/auth/profile/", data, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  searchUsers: (q: string) => api.get<User[]>("/auth/search/", { params: { q } }),
  logout: () => api.post<null>("/auth/logout/"),
  deleteAccount: () => api.delete<null>("/auth/profile/"),
  reportUser: (
    userId: number,
    data: { reason: string; details?: string; conversation_id?: number }
  ) => api.post<{ id: number; reason: string }>(`/auth/users/${userId}/report/`, data),
};

export const chatApi = {
  getConversations: (filter: ChatListFilter = "all") =>
    api.get<Conversation[]>("/chat/conversations/", { params: { filter } }),
  createDirectChat: (user_id: number) =>
    api.post<Conversation>("/chat/conversations/direct/", { user_id }),
  createGroup: (group_name: string, participant_ids: number[]) =>
    api.post<Conversation>("/chat/conversations/group/", { group_name, participant_ids }),
  toggleFavourite: (conversationId: number) =>
    api.post<Conversation>(`/chat/conversations/${conversationId}/favourite/`),
  archiveConversation: (conversationId: number, action: "archive" | "unarchive") =>
    api.post<Conversation>(`/chat/conversations/${conversationId}/archive/`, { action }),
  blockConversation: (conversationId: number, action: "block" | "unblock") =>
    api.post<Conversation>(`/chat/conversations/${conversationId}/block/`, { action }),
  pinConversation: (conversationId: number, action: "pin" | "unpin") =>
    api.post<Conversation>(`/chat/conversations/${conversationId}/pin/`, { action }),
  updateGroup: (conversationId: number, data: FormData) =>
    api.patch<Conversation>(`/chat/conversations/${conversationId}/group/`, data, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  removeGroupMember: (conversationId: number, userId: number) =>
    api.post<Conversation>(`/chat/conversations/${conversationId}/members/${userId}/remove/`),
  getMessages: (conversationId: number, before?: number) =>
    api.get<Message[]>(`/chat/conversations/${conversationId}/messages/`, {
      params: before ? { before } : {},
    }),
  sendMessage: (conversationId: number, data: FormData) =>
    api.post<Message>(`/chat/conversations/${conversationId}/send/`, data, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  deleteMessage: (conversationId: number, messageId: number, deleteFor: "me" | "everyone") =>
    api.delete<{
      id: number;
      conversation: number;
      delete_for: "me" | "everyone";
      hidden?: boolean;
      is_deleted?: boolean;
    }>(`/chat/conversations/${conversationId}/messages/${messageId}/`, {
      data: { delete_for: deleteFor },
    }),
  reactToMessage: (conversationId: number, messageId: number, emoji: string) =>
    api.post<Message>(`/chat/conversations/${conversationId}/messages/${messageId}/react/`, { emoji }),
  markRead: (conversationId: number) =>
    api.post<null>(`/chat/conversations/${conversationId}/read/`),
};

export const storiesApi = {
  getFeed: () => api.get<StatusFeed>("/stories/feed/"),
  createStatus: (data: FormData) =>
    api.post<Status>("/stories/create/", data, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  viewStatus: (statusId: number) => api.post<null>(`/stories/${statusId}/view/`),
  deleteStatus: (statusId: number) => api.delete<null>(`/stories/${statusId}/delete/`),
};

export default api;
