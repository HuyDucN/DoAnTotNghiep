import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { authApi, getApiErrorMessage } from '../../services/api';
import { fullNameSchema } from '../../validation/account';
import { useAuthStore } from '../../store/authStore';
import toast from 'react-hot-toast';
import { Eye, EyeOff } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import './AuthPage.css';

const registerSchema = z.object({
  full_name: fullNameSchema,
  email: z.string().trim().email('Email không hợp lệ'),
  password: z.string().min(8, 'Mật khẩu phải có ít nhất 8 ký tự'),
  confirm: z.string().min(1, 'Vui lòng xác nhận mật khẩu'),
}).refine((data) => data.password === data.confirm, {
  path: ['confirm'],
  message: 'Mật khẩu xác nhận không khớp',
});

type RegisterForm = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
    defaultValues: { full_name: '', email: '', password: '', confirm: '' },
  });

  const onSubmit = async (form: RegisterForm) => {
    const sessionVersion = useAuthStore.getState().sessionVersion;
    try {
      const data = await authApi.register({
        full_name: form.full_name.trim(),
        email: form.email,
        password: form.password,
      });
      if (useAuthStore.getState().sessionVersion !== sessionVersion) return;
      setAuth(data.user, data.access_token);
      toast.success('Tạo tài khoản thành công! 🎉');
      // Mới đăng ký luôn là user, navigate đúng role
      navigate(data.user.role === 'admin' ? '/admin' : '/dashboard');
    } catch (err: unknown) {
      if (useAuthStore.getState().sessionVersion !== sessionVersion) return;
      toast.error(getApiErrorMessage(err, 'Đăng ký thất bại'));
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

        <form onSubmit={handleSubmit(onSubmit)} className="auth-form" noValidate>
          <div className="form-group">
            <label className="form-label">Họ và tên</label>
            <input
              type="text"
              className={`form-input ${errors.full_name ? 'input-error' : ''}`}
              placeholder="Nguyễn Văn A"
              aria-invalid={Boolean(errors.full_name)}
              {...register('full_name')}
            />
            {errors.full_name && <p className="form-error">{errors.full_name.message}</p>}
          </div>

          <div className="form-group">
            <label className="form-label">Email</label>
            <input
              type="email"
              className={`form-input ${errors.email ? 'input-error' : ''}`}
              placeholder="email@example.com"
              aria-invalid={Boolean(errors.email)}
              {...register('email')}
            />
            {errors.email && <p className="form-error">{errors.email.message}</p>}
          </div>

          <div className="form-group">
            <label className="form-label">Mật khẩu</label>
            <div className="input-wrapper">
              <input
                type={showPassword ? 'text' : 'password'}
                className={`form-input ${errors.password ? 'input-error' : ''}`}
                placeholder="Ít nhất 8 ký tự"
                aria-invalid={Boolean(errors.password)}
                {...register('password')}
              />
              <button type="button" className="input-eye-btn" onClick={() => setShowPassword(!showPassword)} tabIndex={-1}>
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {errors.password && <p className="form-error">{errors.password.message}</p>}
          </div>

          <div className="form-group">
            <label className="form-label">Xác nhận mật khẩu</label>
            <div className="input-wrapper">
              <input
                type={showConfirm ? 'text' : 'password'}
                className={`form-input ${errors.confirm ? 'input-error' : ''}`}
                placeholder="Nhập lại mật khẩu"
                aria-invalid={Boolean(errors.confirm)}
                {...register('confirm')}
              />
              <button type="button" className="input-eye-btn" onClick={() => setShowConfirm(!showConfirm)} tabIndex={-1}>
                {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {errors.confirm && <p className="form-error">{errors.confirm.message}</p>}
          </div>

          <button type="submit" className="btn btn-primary btn-full btn-lg" disabled={isSubmitting}>
            {isSubmitting ? <><span className="spinner" />Đang tạo tài khoản...</> : 'Đăng ký'}
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
