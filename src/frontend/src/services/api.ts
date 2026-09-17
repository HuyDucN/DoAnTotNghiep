import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 globally → redirect to login
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

// ── Auth ──────────────────────────────────────────────────────
export const authApi = {
  register: (data: { email: string; password: string; full_name: string }) =>
    api.post('/auth/register', data).then((r) => r.data),

  login: (data: { email: string; password: string }) =>
    api.post('/auth/login', data).then((r) => r.data),

  getMe: () => api.get('/auth/me').then((r) => r.data),

  getProfile: () => api.get('/auth/profile').then((r) => r.data),

  updateProfile: (data: object) => api.put('/auth/profile', data).then((r) => r.data),
};

// ── CV ────────────────────────────────────────────────────────
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

// ── Jobs ──────────────────────────────────────────────────────
export const jobsApi = {
  list: (params?: { category?: string; level?: string; search?: string }) =>
    api.get('/jobs/', { params }).then((r) => r.data),

  get: (id: number) => api.get(`/jobs/${id}`).then((r) => r.data),

  match: (jobId: number, cvId: number) =>
    api.post(`/jobs/${jobId}/match/${cvId}`).then((r) => r.data),

  getGapHistory: () => api.get('/jobs/history/gaps').then((r) => r.data),

  // Admin
  create: (data: object) => api.post('/jobs/admin', data).then((r) => r.data),
  update: (id: number, data: object) => api.put(`/jobs/admin/${id}`, data).then((r) => r.data),
  delete: (id: number) => api.delete(`/jobs/admin/${id}`),
};
