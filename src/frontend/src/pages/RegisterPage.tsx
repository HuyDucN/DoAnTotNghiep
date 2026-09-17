import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { authApi } from '../services/api';
import { useAuthStore } from '../store/authStore';
import toast from 'react-hot-toast';
import './AuthPage.css';

export default function RegisterPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [form, setForm] = useState({ full_name: '', email: '', password: '', confirm: '' });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.full_name || !form.email || !form.password) {
      return toast.error('Vui lòng điền đầy đủ thông tin');
    }
    if (form.password !== form.confirm) {
      return toast.error('Mật khẩu xác nhận không khớp');
    }
    if (form.password.length < 6) {
      return toast.error('Mật khẩu phải có ít nhất 6 ký tự');
    }

    setLoading(true);
    try {
      const data = await authApi.register({
        full_name: form.full_name,
        email: form.email,
        password: form.password,
      });
      setAuth(data.user, data.access_token);
      toast.success('Tạo tài khoản thành công! 🎉');
      navigate('/dashboard');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Đăng ký thất bại');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-bg">
        <div className="auth-orb auth-orb-1" />
        <div className="auth-orb auth-orb-2" />
        <div className="auth-orb auth-orb-3" />
      </div>

      <div className="auth-card animate-fade-in">
        <div className="auth-logo">
          <div className="auth-logo-mark">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
              <rect width="28" height="28" rx="8" fill="url(#grad2)" />
              <path d="M8 14l4 4 8-8" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
              <defs>
                <linearGradient id="grad2" x1="0" y1="0" x2="28" y2="28">
                  <stop stopColor="#6366f1"/><stop offset="1" stopColor="#8b5cf6"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <div>
            <div className="auth-logo-name">CV Skill Gap</div>
            <div className="auth-logo-sub">AI Career Advisor</div>
          </div>
        </div>

        <h1 className="auth-title">Tạo tài khoản</h1>
        <p className="auth-subtitle">Bắt đầu hành trình phát triển kỹ năng với AI.</p>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label className="form-label">Họ và tên</label>
            <input
              type="text"
              className="form-input"
              placeholder="Nguyễn Văn A"
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Email</label>
            <input
              type="email"
              className="form-input"
              placeholder="email@example.com"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Mật khẩu</label>
            <input
              type="password"
              className="form-input"
              placeholder="Ít nhất 6 ký tự"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Xác nhận mật khẩu</label>
            <input
              type="password"
              className="form-input"
              placeholder="Nhập lại mật khẩu"
              value={form.confirm}
              onChange={(e) => setForm({ ...form, confirm: e.target.value })}
            />
          </div>

          <button type="submit" className="btn btn-primary btn-full btn-lg" disabled={loading}>
            {loading ? <><span className="spinner" />Đang tạo tài khoản...</> : 'Đăng ký'}
          </button>
        </form>

        <p className="auth-switch">
          Đã có tài khoản?{' '}
          <Link to="/login" className="auth-link">Đăng nhập</Link>
        </p>
      </div>
    </div>
  );
}
