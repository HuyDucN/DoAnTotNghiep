import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { authApi } from '../../services/api';
import { useAuthStore } from '../../store/authStore';
import toast from 'react-hot-toast';
import { Eye, EyeOff } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import AuthLayout from './AuthLayout';

const loginSchema = z.object({
  email: z.string().trim().email('Email không hợp lệ'),
  password: z.string().min(1, 'Vui lòng nhập mật khẩu'),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [showPassword, setShowPassword] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  });

  const onSubmit = async (form: LoginForm) => {
    const sessionVersion = useAuthStore.getState().sessionVersion;
    try {
      const data = await authApi.login(form);
      if (useAuthStore.getState().sessionVersion !== sessionVersion) return;
      setAuth(data.user, data.access_token);
      toast.success(`Chào mừng, ${data.user.full_name}! 🎉`);
      // Redirect theo role: admin → /admin, recruiter → /admin/jobs, user → /dashboard
      navigate(data.user.role === 'admin' ? '/admin' : data.user.role === 'recruiter' ? '/admin/jobs' : '/dashboard');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Đăng nhập thất bại');
    }
  };

  return (
    <AuthLayout>
        {/* Logo */}
        <div className="auth-logo">
          <div className="auth-logo-mark">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
              <rect width="28" height="28" rx="8" fill="url(#grad)" />
              <path d="M8 14l4 4 8-8" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
              <defs>
                <linearGradient id="grad" x1="0" y1="0" x2="28" y2="28">
                  <stop stopColor="#6366f1"/>
                  <stop offset="1" stopColor="#8b5cf6"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <div>
            <div className="auth-logo-name">CV Skill Gap</div>
            <div className="auth-logo-sub">AI Career Advisor</div>
          </div>
        </div>

        <h1 className="auth-title">Đăng nhập</h1>
        <p className="auth-subtitle">Chào mừng bạn trở lại! Hãy tiếp tục hành trình phát triển kỹ năng.</p>

        <form onSubmit={handleSubmit(onSubmit)} className="auth-form" noValidate>
          <div className="form-group">
            <label className="form-label" htmlFor="login-email">Email</label>
            <input
              type="email"
              id="login-email"
              autoComplete="email"
              className={`form-input ${errors.email ? 'input-error' : ''}`}
              placeholder="email@example.com"
              aria-invalid={Boolean(errors.email)}
              {...register('email')}
            />
            {errors.email && <p className="form-error">{errors.email.message}</p>}
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="login-password">Mật khẩu</label>
            <div className="input-wrapper">
              <input
                type={showPassword ? 'text' : 'password'}
                id="login-password"
                autoComplete="current-password"
                className={`form-input ${errors.password ? 'input-error' : ''}`}
                placeholder="••••••••"
                aria-invalid={Boolean(errors.password)}
                {...register('password')}
              />
              <button
                type="button"
                className="input-eye-btn"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {errors.password && <p className="form-error">{errors.password.message}</p>}
          </div>

          <div className="auth-forgot">
            <Link to="/forgot-password">
              Quên mật khẩu?
            </Link>
          </div>

          <button type="submit" className="btn btn-primary btn-full btn-lg" disabled={isSubmitting}>
            {isSubmitting ? <><span className="spinner" />Đang đăng nhập...</> : 'Đăng nhập'}
          </button>
        </form>

        <p className="auth-switch">
          Chưa có tài khoản?{' '}
          <Link to="/register" className="auth-link">Đăng ký ngay</Link>
        </p>
    </AuthLayout>
  );
}
