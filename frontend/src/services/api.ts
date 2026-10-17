import axios, { isAxiosError } from 'axios';
import { useAuthStore } from '../store/authStore';
import { attachSessionInterceptors } from './sessionInterceptors';
import type { AccountResponse, AccountUpdate } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000, // 60s — AI analysis có thể chậm
});

export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (!isAxiosError(error)) return fallback;
  if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
    return 'Yêu cầu quá thời gian chờ. Vui lòng kiểm tra kết nối và thử lại.';
  }
  if (!error.response) return 'Không thể kết nối đến máy chủ. Vui lòng kiểm tra mạng và backend.';
  const detail: unknown = error.response.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const messages = detail.flatMap((item: unknown) => {
      if (!item || typeof item !== 'object' || !('msg' in item) || typeof item.msg !== 'string') return [];
      return [item.msg.replace(/^Value error, /, '')];
    });
    if (messages.length > 0) return [...new Set(messages)].join('. ');
  }
  if (error.response.status === 503) return 'Dữ liệu tạm thời không khả dụng. Vui lòng thử lại sau.';
  if (error.response.status >= 500) return 'Máy chủ gặp lỗi. Vui lòng thử lại sau.';
  return fallback;
}

attachSessionInterceptors(
  api,
  () => {
    const state = useAuthStore.getState();
    return { version: state.sessionVersion, token: state.token };
  },
  () => {
    useAuthStore.getState().logout();
    window.location.href = '/login';
  },
);

// ── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (data: { email: string; password: string; full_name: string }) =>
    api.post('/auth/register', data).then((r) => r.data),

  login: (data: { email: string; password: string }) =>
    api.post('/auth/login', data).then((r) => r.data),

  logout: () =>
    api.post('/auth/logout').then((r) => r.data),

  forgotPassword: (email: string) =>
    api.post('/auth/forgot-password', { email }).then((r) => r.data),

  resetPassword: (token: string, new_password: string) =>
    api.post<{ message: string; user_id: number }>('/auth/reset-password', { token, new_password }).then((r) => r.data),
};

// ── Users / Profile ──────────────────────────────────────────────────────────
export const usersApi = {
  getAccount: () => api.get<AccountResponse>('/users/me/account').then((r) => r.data),

  updateAccount: (data: AccountUpdate) =>
    api.put<AccountResponse>('/users/me/account', data).then((r) => r.data),

  // GET /users/me — lấy thông tin user từ JWT (không từ URL)
  getMe: () => api.get('/users/me').then((r) => r.data),

  // PUT /users/me — cập nhật full_name
  updateMe: (data: { full_name?: string }) =>
    api.put('/users/me', data).then((r) => r.data),

  // GET /users/me/profile — profile chi tiết
  getProfile: () => api.get('/users/me/profile').then((r) => r.data),

  // PUT /users/me/profile — cập nhật profile
  updateProfile: (data: object) =>
    api.put('/users/me/profile', data).then((r) => r.data),

  // PUT /users/me/password — đổi mật khẩu (cần biết mật khẩu cũ)
  changePassword: (data: { old_password: string; new_password: string }) =>
    api.put('/users/me/password', data).then((r) => r.data),
};

// Giữ lại authApi.getProfile để tương thích ngược
export const authApi_compat = {
  getProfile: () => usersApi.getProfile(),
  updateProfile: (data: object) => usersApi.updateProfile(data),
};

// ── CV ────────────────────────────────────────────────────────────────────────
export const cvApi = {
  upload: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/cv/upload', formData, {
      // Let the browser/axios add the multipart boundary automatically.
    }).then((r) => r.data);
  },

  list: () => api.get('/cv/list').then((r) => r.data),

  get: (id: number) => api.get(`/cv/${id}`).then((r) => r.data),

  status: (id: number) => api.get(`/cv/${id}/status`).then((r) => r.data),

  skills: (id: number) => api.get(`/cv/${id}/skills`).then((r) => r.data),
  addSkill: (id: number, data: { skill_name: string; proficiency_level: string; years_experience: number }) =>
    api.post(`/cv/${id}/skills`, data).then((r) => r.data),
  deleteSkill: (id: number, skillId: number) => api.delete(`/cv/${id}/skills/${skillId}`),

  viewFile: async (id: number, filename: string) => {
    const response = await api.get(`/cv/${id}/file`, { responseType: 'blob' });
    const url = URL.createObjectURL(response.data);
    const tab = window.open(url, '_blank', 'noopener,noreferrer');
    if (!tab) throw new Error('Popup bị chặn');
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
    return filename;
  },

  delete: (id: number) => api.delete(`/cv/${id}`),

  reanalyze: (id: number) => api.post(`/cv/${id}/reanalyze`).then((r) => r.data),
};

// ── Jobs ──────────────────────────────────────────────────────────────────────
export const jobsApi = {
  list: (params?: { category?: string; level?: string; search?: string; page?: number; size?: number }) =>
    api.get('/jobs/', { params }).then((r) => r.data),

  get: (id: number) => api.get(`/jobs/${id}`).then((r) => r.data),

  // POST /jobs/{jobId}/match/{cvId} → Match Score + Skill Gap + AI Recommendation
  match: (jobId: number, cvId: number) =>
    api.post(`/jobs/${jobId}/match/${cvId}`).then((r) => r.data),

  // GET /jobs/history/gaps — lịch sử phân tích Skill Gap
  getGapHistory: () => api.get('/jobs/history/gaps').then((r) => r.data),

  // Admin
  listAdmin: (params?: { category?: string; search?: string; page?: number; size?: number }) =>
    api.get('/jobs/admin/list', { params }).then((r) => r.data),
  parseDescription: (description: string) =>
    api.post('/jobs/admin/parse-description', { description }).then((r) => r.data),
  create: (data: object) => api.post('/jobs/admin', data).then((r) => r.data),
  update: (id: number, data: object) => api.put(`/jobs/admin/${id}`, data).then((r) => r.data),
  delete: (id: number) => api.delete(`/jobs/admin/${id}`),
};

// ── Skills ────────────────────────────────────────────────────────────────────
export const skillsApi = {
  list: (params?: { category?: string; search?: string; page?: number; size?: number }) =>
    api.get('/skills/', { params }).then((r) => r.data),

  // Admin
  create: (data: { name: string; category: string; description?: string }) =>
    api.post('/skills/', data).then((r) => r.data),
  update: (id: number, data: object) => api.put(`/skills/${id}`, data).then((r) => r.data),
  delete: (id: number) => api.delete(`/skills/${id}`),
};

export const adminApi = {
  users: (params?: { page?: number; size?: number; search?: string }) =>
    api.get('/admin/users', { params }).then((r) => r.data),
  updateUserActive: (id: number, is_active: boolean) =>
    api.patch(`/admin/users/${id}/active`, { is_active }).then((r) => r.data),
  cvs: (params?: { page?: number; size?: number }) =>
    api.get('/admin/cvs', { params }).then((r) => r.data),
  deleteCv: (id: number) => api.delete(`/admin/cvs/${id}`),
};
