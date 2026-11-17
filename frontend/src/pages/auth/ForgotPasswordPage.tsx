import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { authApi } from '../../services/api';
import toast from 'react-hot-toast';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import AuthLayout from './AuthLayout';

const forgotPasswordSchema = z.object({
  email: z.string().trim().email('Email không hợp lệ'),
});

type ForgotPasswordForm = z.infer<typeof forgotPasswordSchema>;

export default function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [devToken, setDevToken] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordForm>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: '' },
  });

  const onSubmit = async ({ email }: ForgotPasswordForm) => {
    try {
      const data = await authApi.forgotPassword(email);
      toast.success(data.message || 'Yêu cầu thành công');
      if (data.devResetToken) {
        setDevToken(data.devResetToken);
      } else {
        setTimeout(() => navigate('/login'), 3000);
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Có lỗi xảy ra');
    }
  };

  const handleCopyToken = () => {
    if (!devToken) return;
    navigator.clipboard.writeText(devToken);
    toast.success('Đã copy mã khôi phục!');
  };

  return (
    <AuthLayout>
        <div className="auth-logo">
          <div className="auth-logo-mark">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
              <rect width="28" height="28" rx="8" fill="url(#forgot-grad)" />
              <path d="M8 14l4 4 8-8" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              <defs>
                <linearGradient id="forgot-grad" x1="0" y1="0" x2="28" y2="28">
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

        <h1 className="auth-title">Quên mật khẩu</h1>
        <p className="auth-subtitle">Nhập email của bạn để nhận hướng dẫn đặt lại mật khẩu.</p>

        {!devToken ? (
          <form onSubmit={handleSubmit(onSubmit)} className="auth-form" noValidate>
            <div className="form-group">
              <label className="form-label" htmlFor="recovery-email">Email</label>
              <input
                type="email"
                id="recovery-email"
                autoComplete="email"
                className={`form-input ${errors.email ? 'input-error' : ''}`}
                placeholder="email@example.com"
                aria-invalid={Boolean(errors.email)}
                {...register('email')}
              />
              {errors.email && <p className="form-error">{errors.email.message}</p>}
            </div>
            <button type="submit" className="btn btn-primary btn-full btn-lg" disabled={isSubmitting}>
              {isSubmitting ? <><span className="spinner" />Đang gửi...</> : 'Gửi yêu cầu'}
            </button>
          </form>
        ) : (
          <div className="auth-form" style={{ textAlign: 'center' }}>
            <div className="auth-recovery-info">
              <p>Mã khôi phục (chế độ thử nghiệm):</p>
              <code>{devToken}</code>
            </div>
            <div style={{ display: 'flex', gap: '10px', flexDirection: 'column' }}>
              <button type="button" className="btn btn-outline btn-full" onClick={handleCopyToken}>Sao chép mã khôi phục</button>
              <button type="button" className="btn btn-primary btn-full" onClick={() => navigate('/reset-password', { state: { token: devToken } })}>
                Tiếp tục đặt lại mật khẩu
              </button>
            </div>
          </div>
        )}

        <p className="auth-switch" style={{ marginTop: '1.5rem' }}>
          <Link to="/login" className="auth-link">Quay lại đăng nhập</Link>
        </p>
    </AuthLayout>
  );
}
