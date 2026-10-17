import { useEffect, useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { isCancel } from 'axios';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { useAuthStore } from '../../store/authStore';
import { getApiErrorMessage, usersApi } from '../../services/api';
import { profileSchema } from '../../validation/account';
import type { AccountResponse } from '../../types';
import { Settings, User, Lock, Globe, Save, Loader2, Eye, EyeOff } from 'lucide-react';
import toast from 'react-hot-toast';
import './SettingsPage.css';

type Tab = 'profile' | 'password';

const passwordSchema = z.object({
  old_password: z.string().min(1, 'Vui lòng nhập mật khẩu hiện tại'),
  new_password: z.string().min(8, 'Mật khẩu mới phải có ít nhất 8 ký tự'),
  confirm_password: z.string().min(1, 'Vui lòng xác nhận mật khẩu'),
}).refine((data) => data.new_password === data.confirm_password, {
  path: ['confirm_password'],
  message: 'Mật khẩu xác nhận không khớp',
});

type ProfileForm = z.infer<typeof profileSchema>;
type PasswordForm = z.infer<typeof passwordSchema>;

const emptyProfile: ProfileForm = {
  full_name: '',
  phone: '',
  location: '',
  job_title: '',
  bio: '',
  linkedin_url: '',
  github_url: '',
};

function accountFormValues(account: AccountResponse): ProfileForm {
  return {
    full_name: account.user.full_name,
    phone: account.profile?.phone || '',
    location: account.profile?.location || '',
    job_title: account.profile?.job_title || '',
    bio: account.profile?.bio || '',
    linkedin_url: account.profile?.linkedin_url || '',
    github_url: account.profile?.github_url || '',
  };
}

export default function SettingsPage() {
  const navigate = useNavigate();
  const { user, updateUser } = useAuthStore();
  const [activeTab, setActiveTab] = useState<Tab>('profile');
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [saving, setSaving] = useState(false);
  const [showOld, setShowOld] = useState(false);
  const [showNew, setShowNew] = useState(false);

  const {
    register: registerProfile,
    handleSubmit: handleProfileSubmit,
    reset: resetProfile,
    control: profileControl,
    formState: { errors: profileErrors },
  } = useForm<ProfileForm>({
    resolver: zodResolver(profileSchema),
    defaultValues: emptyProfile,
  });

  const {
    register: registerPassword,
    handleSubmit: handlePasswordSubmit,
    formState: { errors: passwordErrors },
  } = useForm<PasswordForm>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { old_password: '', new_password: '', confirm_password: '' },
  });

  const fullName = useWatch({ control: profileControl, name: 'full_name' });

  useEffect(() => {
    let active = true;
    const sessionVersion = useAuthStore.getState().sessionVersion;
    const isCurrent = () => active && useAuthStore.getState().sessionVersion === sessionVersion;
    usersApi.getAccount()
      .then((account) => {
        if (!isCurrent()) return;
        resetProfile(accountFormValues(account));
        updateUser({ full_name: account.user.full_name });
      })
      .catch((error: unknown) => {
        if (!isCurrent() || isCancel(error)) return;
        setLoadError(getApiErrorMessage(error, 'Lỗi tải thông tin hồ sơ'));
      })
      .finally(() => { if (isCurrent()) setLoading(false); });
    return () => { active = false; };
  }, [resetProfile, updateUser, loadAttempt]);

  const handleSaveProfile = async (data: ProfileForm) => {
    if (loading || loadError || saving) return;
    const sessionVersion = useAuthStore.getState().sessionVersion;
    setSaving(true);
    try {
      const account = await usersApi.updateAccount(data);
      if (useAuthStore.getState().sessionVersion !== sessionVersion) return;
      updateUser({ full_name: account.user.full_name });
      resetProfile(accountFormValues(account));
      toast.success('Cập nhật hồ sơ thành công!');
    } catch (e: unknown) {
      if (isCancel(e) || useAuthStore.getState().sessionVersion !== sessionVersion) return;
      toast.error(getApiErrorMessage(e, 'Lỗi cập nhật hồ sơ'));
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async (data: PasswordForm) => {
    const session = useAuthStore.getState();
    if (!session.user) return;
    setSaving(true);
    try {
      await usersApi.changePassword({
        old_password: data.old_password,
        new_password: data.new_password,
      });
      if (!useAuthStore.getState().logoutIfCurrentSession(session.sessionVersion, session.user.id)) return;
      toast.success('Đổi mật khẩu thành công! Vui lòng đăng nhập lại.');
      navigate('/login', { replace: true });
    } catch (e: any) {
      if (isCancel(e) || useAuthStore.getState().sessionVersion !== session.sessionVersion) return;
      toast.error(e.response?.data?.detail || 'Lỗi đổi mật khẩu');
    } finally {
      setSaving(false);
    }
  };

  const fieldError = (message?: string) => message && <p className="input-hint text-danger">{message}</p>;

  return (
    <div className="settings-page animate-fade-in">
      <div className="settings-header">
        <h2 className="flex items-center gap-2"><Settings size={22} className="text-brand" />Cài đặt tài khoản</h2>
        <p className="text-secondary text-sm mt-1">Quản lý thông tin cá nhân và bảo mật tài khoản</p>
      </div>

      <div className="settings-layout">
        <nav className="settings-nav card">
          <button className={`settings-tab ${activeTab === 'profile' ? 'active' : ''}`} disabled={saving} onClick={() => setActiveTab('profile')}>
            <User size={16} /> Hồ sơ cá nhân
          </button>
          <button className={`settings-tab ${activeTab === 'password' ? 'active' : ''}`} disabled={saving} onClick={() => setActiveTab('password')}>
            <Lock size={16} /> Đổi mật khẩu
          </button>
        </nav>

        <div className="settings-content card">
          {loading ? (
            <div className="flex justify-center p-10"><Loader2 className="animate-spin text-brand" size={28} /></div>
          ) : activeTab === 'profile' && loadError ? (
            <div className="settings-section" role="alert">
              <p className="text-danger mb-4">{loadError}</p>
              <button type="button" className="btn btn-primary" onClick={() => {
                setLoading(true);
                setLoadError(null);
                setLoadAttempt((attempt) => attempt + 1);
              }}>Thử tải lại</button>
            </div>
          ) : activeTab === 'profile' ? (
            <form className="settings-section" onSubmit={handleProfileSubmit(handleSaveProfile)} noValidate>
              <div className="section-title"><User size={18} className="text-brand" /><h3>Thông tin cá nhân</h3></div>

              <div className="avatar-section mb-6">
                <div className="settings-avatar bg-brand">{(fullName || 'U').charAt(0).toUpperCase()}</div>
                <div>
                  <p className="font-semibold">{user?.email}</p>
                  <span className={`badge ${user?.role === 'admin' ? 'badge-primary' : 'badge-neutral'}`}>
                    {user?.role === 'admin' ? 'Quản trị viên' : 'Người dùng'}
                  </span>
                </div>
              </div>

              <div className="form-grid">
                <div className="form-group">
                  <label className="form-label">Họ và tên *</label>
                  <input className={`form-input ${profileErrors.full_name ? 'input-error' : ''}`} placeholder="Nguyễn Văn A" readOnly={saving} aria-invalid={Boolean(profileErrors.full_name)} {...registerProfile('full_name')} />
                  {fieldError(profileErrors.full_name?.message)}
                </div>
                <div className="form-group">
                  <label className="form-label">Chức danh</label>
                  <input className={`form-input ${profileErrors.job_title ? 'input-error' : ''}`} placeholder="Full-stack Developer" readOnly={saving} {...registerProfile('job_title')} />
                  {fieldError(profileErrors.job_title?.message)}
                </div>
                <div className="form-group">
                  <label className="form-label">Số điện thoại</label>
                  <input className={`form-input ${profileErrors.phone ? 'input-error' : ''}`} placeholder="0901234567" readOnly={saving} {...registerProfile('phone')} />
                  {fieldError(profileErrors.phone?.message)}
                </div>
                <div className="form-group">
                  <label className="form-label">Địa điểm</label>
                  <input className={`form-input ${profileErrors.location ? 'input-error' : ''}`} placeholder="Hà Nội, Việt Nam" readOnly={saving} {...registerProfile('location')} />
                  {fieldError(profileErrors.location?.message)}
                </div>
                <div className="form-group form-group-full">
                  <label className="form-label">Giới thiệu bản thân</label>
                  <textarea className={`form-input form-textarea ${profileErrors.bio ? 'input-error' : ''}`} placeholder="Mô tả ngắn về bản thân, kinh nghiệm và mục tiêu nghề nghiệp..." readOnly={saving} rows={3} {...registerProfile('bio')} />
                  {fieldError(profileErrors.bio?.message)}
                </div>
              </div>

              <div className="section-title mt-6"><Globe size={18} className="text-brand" /><h3>Liên kết mạng xã hội</h3></div>
              <div className="form-grid">
                <div className="form-group">
                  <label className="form-label">LinkedIn URL</label>
                  <input className={`form-input ${profileErrors.linkedin_url ? 'input-error' : ''}`} placeholder="https://linkedin.com/in/yourprofile" readOnly={saving} {...registerProfile('linkedin_url')} />
                  {fieldError(profileErrors.linkedin_url?.message)}
                </div>
                <div className="form-group">
                  <label className="form-label">GitHub URL</label>
                  <input className={`form-input ${profileErrors.github_url ? 'input-error' : ''}`} placeholder="https://github.com/yourusername" readOnly={saving} {...registerProfile('github_url')} />
                  {fieldError(profileErrors.github_url?.message)}
                </div>
              </div>

              <div className="form-actions">
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? <Loader2 className="animate-spin" size={16} /> : <Save size={16} />}Lưu thay đổi
                </button>
              </div>
            </form>
          ) : (
            <form className="settings-section" onSubmit={handlePasswordSubmit(handleChangePassword)} noValidate>
              <div className="section-title"><Lock size={18} className="text-brand" /><h3>Đổi mật khẩu</h3></div>
              <p className="text-secondary text-sm mb-6">Nhập mật khẩu hiện tại để đặt mật khẩu mới. Sau khi đổi, bạn cần đăng nhập lại trên tất cả thiết bị.</p>

              <div className="form-stack">
                <div className="form-group">
                  <label className="form-label">Mật khẩu hiện tại</label>
                  <div className="input-pw-wrap">
                    <input className={`form-input ${passwordErrors.old_password ? 'input-error' : ''}`} type={showOld ? 'text' : 'password'} placeholder="••••••••" {...registerPassword('old_password')} />
                    <button type="button" className="pw-toggle" onClick={() => setShowOld(!showOld)} aria-label="Hiện hoặc ẩn mật khẩu hiện tại">{showOld ? <EyeOff size={16} /> : <Eye size={16} />}</button>
                  </div>
                  {fieldError(passwordErrors.old_password?.message)}
                </div>

                <div className="form-group">
                  <label className="form-label">Mật khẩu mới <span className="text-muted">(tối thiểu 8 ký tự)</span></label>
                  <div className="input-pw-wrap">
                    <input className={`form-input ${passwordErrors.new_password ? 'input-error' : ''}`} type={showNew ? 'text' : 'password'} placeholder="••••••••" {...registerPassword('new_password')} />
                    <button type="button" className="pw-toggle" onClick={() => setShowNew(!showNew)} aria-label="Hiện hoặc ẩn mật khẩu mới">{showNew ? <EyeOff size={16} /> : <Eye size={16} />}</button>
                  </div>
                  {fieldError(passwordErrors.new_password?.message)}
                </div>

                <div className="form-group">
                  <label className="form-label">Xác nhận mật khẩu mới</label>
                  <input className={`form-input ${passwordErrors.confirm_password ? 'input-error' : ''}`} type="password" placeholder="••••••••" {...registerPassword('confirm_password')} />
                  {fieldError(passwordErrors.confirm_password?.message)}
                </div>
              </div>

              <div className="form-actions">
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? <Loader2 className="animate-spin" size={16} /> : <Lock size={16} />}Đổi mật khẩu
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
