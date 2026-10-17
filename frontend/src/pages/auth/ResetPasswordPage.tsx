import { useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { isCancel } from 'axios';
import { authApi } from '../../services/api';
import { useAuthStore } from '../../store/authStore';
import toast from 'react-hot-toast';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import './AuthPage.css';

const resetPasswordSchema = z.object({
  token: z.string().trim().min(1, 'Vui lòng nhập mã khôi phục'),
  new_password: z.string().min(8, 'Mật khẩu phải có ít nhất 8 ký tự'),
  confirm_password: z.string().min(1, 'Vui lòng xác nhận mật khẩu'),
}).refine((data) => data.new_password === data.confirm_password, {
  path: ['confirm_password'],
  message: 'Mật khẩu xác nhận không khớp',
});

type ResetPasswordForm = z.infer<typeof resetPasswordSchema>;

export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordForm>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { token: '', new_password: '', confirm_password: '' },
  });

  useEffect(() => {
    const token = location.state?.token;
    if (typeof token === 'string' && token) {
      setValue('token', token, { shouldValidate: true });
    }
  }, [location.state, setValue]);

  const onSubmit = async (form: ResetPasswordForm) => {
    const sessionVersion = useAuthStore.getState().sessionVersion;
    try {
      const result = await authApi.resetPassword(form.token, form.new_password);
      if (useAuthStore.getState().sessionVersion !== sessionVersion) return;
      useAuthStore.getState().logoutIfCurrentSession(sessionVersion, result.user_id);
      toast.success('Đặt lại mật khẩu thành công! Bạn có thể đăng nhập ngay.');
      navigate('/login', { replace: true });
    } catch (err: any) {
      if (isCancel(err) || useAuthStore.getState().sessionVersion !== sessionVersion) return;
      toast.error(err.response?.data?.detail || 'Đặt lại mật khẩu thất bại');
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
              <rect width="28" height="28" rx="8" fill="url(#reset-grad)" />
              <path d="M8 14l4 4 8-8" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              <defs>
                <linearGradient id="reset-grad" x1="0" y1="0" x2="28" y2="28">
                  <stop stopColor="#6366f1" /><stop offset="1" stopColor="#8b5cf6" />
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

        <form onSubmit={handleSubmit(onSubmit)} className="auth-form" noValidate>
          <div className="form-group">
            <label className="form-label">Mã khôi phục (Token)</label>
            <input
              type="text"
              className={`form-input ${errors.token ? 'input-error' : ''}`}
              placeholder="Nhập hoặc dán token..."
              aria-invalid={Boolean(errors.token)}
              {...register('token')}
            />
            {errors.token && <p className="form-error">{errors.token.message}</p>}
          </div>
          <div className="form-group">
            <label className="form-label">Mật khẩu mới</label>
            <input
              type="password"
              className={`form-input ${errors.new_password ? 'input-error' : ''}`}
              placeholder="Ít nhất 8 ký tự"
              aria-invalid={Boolean(errors.new_password)}
              {...register('new_password')}
            />
            {errors.new_password && <p className="form-error">{errors.new_password.message}</p>}
          </div>
          <div className="form-group">
            <label className="form-label">Xác nhận mật khẩu</label>
            <input
              type="password"
              className={`form-input ${errors.confirm_password ? 'input-error' : ''}`}
              placeholder="Nhập lại mật khẩu mới"
              aria-invalid={Boolean(errors.confirm_password)}
              {...register('confirm_password')}
            />
            {errors.confirm_password && <p className="form-error">{errors.confirm_password.message}</p>}
          </div>
          <button type="submit" className="btn btn-primary btn-full btn-lg" disabled={isSubmitting}>
            {isSubmitting ? <><span className="spinner" />Đang xử lý...</> : 'Đặt lại mật khẩu'}
          </button>
        </form>
        <p className="auth-switch"><Link to="/login" className="auth-link">Quay lại đăng nhập</Link></p>
      </div>
    </div>
  );
}
