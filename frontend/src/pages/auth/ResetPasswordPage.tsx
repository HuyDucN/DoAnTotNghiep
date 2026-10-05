import { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { authApi } from '../../services/api';
import toast from 'react-hot-toast';
import './AuthPage.css';

export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const location = useLocation();
  
  const [form, setForm] = useState({
    token: '',
    new_password: '',
    confirm_password: ''
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // If token was passed via navigate state from ForgotPasswordPage
    if (location.state?.token) {
      setForm(prev => ({ ...prev, token: location.state.token }));
    }
  }, [location]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.token || !form.new_password || !form.confirm_password) {
      return toast.error('Vui lòng điền đầy đủ thông tin');
    }
    
    if (form.new_password !== form.confirm_password) {
      return toast.error('Mật khẩu xác nhận không khớp');
    }
    
    if (form.new_password.length < 8) {
      return toast.error('Mật khẩu phải có ít nhất 8 ký tự');
    }

    setLoading(true);
    try {
      await authApi.resetPassword(form.token, form.new_password);
      toast.success('Đặt lại mật khẩu thành công! Bạn có thể đăng nhập ngay.');
      navigate('/login');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Đặt lại mật khẩu thất bại');
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

        <h1 className="auth-title">Đặt lại mật khẩu</h1>
        <p className="auth-subtitle">Nhập mã khôi phục và mật khẩu mới của bạn.</p>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label className="form-label">Mã khôi phục (Token)</label>
            <input
              type="text"
              className="form-input"
              placeholder="Nhập hoặc dán token..."
              value={form.token}
              onChange={(e) => setForm({ ...form, token: e.target.value })}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Mật khẩu mới</label>
            <input
              type="password"
              className="form-input"
              placeholder="Ít nhất 8 ký tự"
              value={form.new_password}
              onChange={(e) => setForm({ ...form, new_password: e.target.value })}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Xác nhận mật khẩu</label>
            <input
              type="password"
              className="form-input"
              placeholder="Nhập lại mật khẩu mới"
              value={form.confirm_password}
              onChange={(e) => setForm({ ...form, confirm_password: e.target.value })}
            />
          </div>

          <button type="submit" className="btn btn-primary btn-full btn-lg" disabled={loading}>
            {loading ? <><span className="spinner" />Đang xử lý...</> : 'Cập nhật mật khẩu'}
          </button>
        </form>

        <p className="auth-switch" style={{ marginTop: '1.5rem' }}>
          <Link to="/login" className="auth-link">Quay lại đăng nhập</Link>
        </p>
      </div>
    </div>
  );
}
