import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auto-refresh on 401
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = localStorage.getItem("refresh_token");
      if (refresh) {
        try {
          const { data } = await api.post("/api/v1/auth/token/refresh/", { refresh });
          localStorage.setItem("access_token", data.access);
          original.headers.Authorization = `Bearer ${data.access}`;
          return api(original);
        } catch {
          localStorage.clear();
          window.location.href = "/login";
          return Promise.reject(error);
        }
      } else {
        // No refresh token — session is fully expired
        localStorage.clear();
        window.location.href = "/login";
        return Promise.reject(error);
      }
    }
    return Promise.reject(error);
  }
);

export default api;

// Typed API helpers
export const authApi = {
  login: (username: string, password: string) =>
    api.post("/api/v1/auth/login/", { username, password }),
  register: (data: Record<string, string>) =>
    api.post("/api/v1/auth/register/", data),
  me: () => api.get("/api/v1/auth/me/"),
};

export const inboxApi = {
  conversations: (params?: Record<string, string>) =>
    api.get("/api/v1/inbox/conversations/", { params }),
  messages: (conversationId: string, params?: Record<string, string>) =>
    api.get(`/api/v1/inbox/conversations/${conversationId}/messages/`, { params }),
  markRead: (conversationId: string) =>
    api.post(`/api/v1/inbox/conversations/${conversationId}/read/`),
};

export const aiApi = {
  toggleBot: (conversationId: string, botActive: boolean) =>
    api.post(`/api/v1/ai/conversations/${conversationId}/bot/`, { bot_active: botActive }),
  assignAgent: (conversationId: string, agentId: string | null) =>
    api.post(`/api/v1/ai/conversations/${conversationId}/assign/`, { agent_id: agentId }),
  webhookInfo: () => api.get("/api/v1/ai/webhook-info/"),
  sendTest: (data: { integration_id: string; to: string; message: string }) =>
    api.post("/api/v1/ai/send-test/", data),
};

export const channelsApi = {
  list: () => api.get("/api/v1/channels/integrations/"),
  create: (data: Record<string, unknown>) =>
    api.post("/api/v1/channels/integrations/", data),
  update: (id: string, data: Record<string, unknown>) =>
    api.patch(`/api/v1/channels/integrations/${id}/`, data),
  delete: (id: string) => api.delete(`/api/v1/channels/integrations/${id}/`),
};

export const automationApi = {
  // Auto-post configs
  listConfigs: () => api.get("/api/v1/automation/configs/"),
  createConfig: (data: Record<string, unknown>) =>
    api.post("/api/v1/automation/configs/", data),
  updateConfig: (id: string, data: Record<string, unknown>) =>
    api.patch(`/api/v1/automation/configs/${id}/`, data),
  deleteConfig: (id: string) =>
    api.delete(`/api/v1/automation/configs/${id}/`),
  triggerNow: (id: string) =>
    api.post(`/api/v1/automation/configs/${id}/trigger_now/`),
  postLogs: (id: string) =>
    api.get(`/api/v1/automation/configs/${id}/post_logs/`),
  moderationLogs: (id: string) =>
    api.get(`/api/v1/automation/configs/${id}/moderation_logs/`),
  // Media library
  listMedia: (params?: Record<string, string>) =>
    api.get("/api/v1/automation/media/", { params }),
  uploadMedia: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post("/api/v1/automation/media/", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  deleteMedia: (id: string) =>
    api.delete(`/api/v1/automation/media/${id}/`),
  markUnused: (id: string) =>
    api.post(`/api/v1/automation/media/${id}/mark_unused/`),
  bulkMarkUnused: () =>
    api.post("/api/v1/automation/media/bulk_mark_unused/"),
};
