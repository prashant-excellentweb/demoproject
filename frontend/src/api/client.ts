import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "/api";

const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
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
    api.post("/auth/send-otp/", { phone_number }),
  verifyOtp: (phone_number: string, otp_code: string) =>
    api.post("/auth/verify-otp/", { phone_number, otp_code }),
  getProfile: () => api.get("/auth/profile/"),
  updateProfile: (data: FormData) =>
    api.patch("/auth/profile/", data, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  searchUsers: (q: string) => api.get("/auth/search/", { params: { q } }),
  logout: () => api.post("/auth/logout/"),
};

export const chatApi = {
  getConversations: () => api.get("/chat/conversations/"),
  createDirectChat: (user_id: number) =>
    api.post("/chat/conversations/direct/", { user_id }),
  createGroup: (group_name: string, participant_ids: number[]) =>
    api.post("/chat/conversations/group/", { group_name, participant_ids }),
  getMessages: (conversationId: number, before?: number) =>
    api.get(`/chat/conversations/${conversationId}/messages/`, {
      params: before ? { before } : {},
    }),
  sendMessage: (conversationId: number, data: FormData) =>
    api.post(`/chat/conversations/${conversationId}/send/`, data, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  markRead: (conversationId: number) =>
    api.post(`/chat/conversations/${conversationId}/read/`),
};

export const storiesApi = {
  getFeed: () => api.get("/stories/feed/"),
  createStatus: (data: FormData) =>
    api.post("/stories/create/", data, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  viewStatus: (statusId: number) => api.post(`/stories/${statusId}/view/`),
  deleteStatus: (statusId: number) => api.delete(`/stories/${statusId}/delete/`),
};

export default api;
