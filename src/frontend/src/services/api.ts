import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000, // 60s — AI analysis có thể chậm
});

// Đính JWT vào mọi request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 401 global → xóa token và redirect về login
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
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
    api.post('/auth/reset-password', { token, new_password }).then((r) => r.data),
};

// ── Users / Profile ──────────────────────────────────────────────────────────
export const usersApi = {
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
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((r) => r.data);
  },

  list: () => api.get('/cv/list').then((r) => r.data),

  get: (id: number) => api.get(`/cv/${id}`).then((r) => r.data),

  delete: (id: number) => api.delete(`/cv/${id}`),

  reanalyze: (id: number) => api.post(`/cv/${id}/reanalyze`).then((r) => r.data),
};

// ── Jobs ──────────────────────────────────────────────────────────────────────
export const jobsApi = {
  list: (params?: { category?: string; level?: string; search?: string }) =>
    api.get('/jobs/', { params }).then((r) => r.data),

  get: (id: number) => api.get(`/jobs/${id}`).then((r) => r.data),

  // POST /jobs/{jobId}/match/{cvId} → Match Score + Skill Gap + AI Recommendation
  match: (jobId: number, cvId: number) =>
    api.post(`/jobs/${jobId}/match/${cvId}`).then((r) => r.data),

  // GET /jobs/history/gaps — lịch sử phân tích Skill Gap
  getGapHistory: () => api.get('/jobs/history/gaps').then((r) => r.data),

  // Admin
  create: (data: object) => api.post('/jobs/admin', data).then((r) => r.data),
  update: (id: number, data: object) => api.put(`/jobs/admin/${id}`, data).then((r) => r.data),
  delete: (id: number) => api.delete(`/jobs/admin/${id}`),
};

// ── Skills ────────────────────────────────────────────────────────────────────
export const skillsApi = {
  list: (params?: { category?: string; search?: string }) =>
    api.get('/skills/', { params }).then((r) => r.data),

  // Admin
  create: (data: { name: string; category: string; description?: string }) =>
    api.post('/skills/', data).then((r) => r.data),
  update: (id: number, data: object) => api.put(`/skills/${id}`, data).then((r) => r.data),
  delete: (id: number) => api.delete(`/skills/${id}`),
};
