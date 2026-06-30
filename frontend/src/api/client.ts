import axios, { type AxiosResponse } from "axios";

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

export const authApi = {
  sendOtp: (phone_number: string) =>
    api.post<ApiResponse<{ phone_number: string }>>("/auth/send-otp/", { phone_number }),
  verifyOtp: (phone_number: string, otp_code: string) =>
    api.post<ApiResponse<{ access: string; refresh: string; user: import("@/types").User; is_new_user: boolean }>>(
      "/auth/verify-otp/",
      { phone_number, otp_code }
    ),
  getProfile: () => api.get<ApiResponse<import("@/types").User>>("/auth/profile/"),
  updateProfile: (data: FormData) =>
    api.patch<ApiResponse<import("@/types").User>>("/auth/profile/", data, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  searchUsers: (q: string) =>
    api.get<ApiResponse<import("@/types").User[]>>("/auth/search/", { params: { q } }),
  logout: () => api.post<ApiResponse<null>>("/auth/logout/"),
};

export const chatApi = {
  getConversations: () => api.get<ApiResponse<import("@/types").Conversation[]>>("/chat/conversations/"),
  createDirectChat: (user_id: number) =>
    api.post<ApiResponse<import("@/types").Conversation>>("/chat/conversations/direct/", { user_id }),
  createGroup: (group_name: string, participant_ids: number[]) =>
    api.post<ApiResponse<import("@/types").Conversation>>("/chat/conversations/group/", {
      group_name,
      participant_ids,
    }),
  getMessages: (conversationId: number, before?: number) =>
    api.get<ApiResponse<import("@/types").Message[]>>(`/chat/conversations/${conversationId}/messages/`, {
      params: before ? { before } : {},
    }),
  sendMessage: (conversationId: number, data: FormData) =>
    api.post<ApiResponse<import("@/types").Message>>(`/chat/conversations/${conversationId}/send/`, data, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  markRead: (conversationId: number) =>
    api.post<ApiResponse<null>>(`/chat/conversations/${conversationId}/read/`),
};

export const storiesApi = {
  getFeed: () => api.get<ApiResponse<import("@/types").StatusFeed>>("/stories/feed/"),
  createStatus: (data: FormData) =>
    api.post<ApiResponse<import("@/types").Status>>("/stories/create/", data, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  viewStatus: (statusId: number) => api.post<ApiResponse<null>>(`/stories/${statusId}/view/`),
  deleteStatus: (statusId: number) => api.delete<ApiResponse<null>>(`/stories/${statusId}/delete/`),
};

export default api;
