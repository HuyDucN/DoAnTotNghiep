import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../store/authStore';
import { usersApi } from '../services/api';
import type { Profile } from '../types';
import { Settings, User, Lock, Globe, Save, Loader2, Eye, EyeOff } from 'lucide-react';
import toast from 'react-hot-toast';
import './SettingsPage.css';

type Tab = 'profile' | 'password';

export default function SettingsPage() {
  const { user, updateUser } = useAuthStore();
  const [activeTab, setActiveTab] = useState<Tab>('profile');
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Profile form
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [location, setLocation] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [bio, setBio] = useState('');
  const [linkedinUrl, setLinkedinUrl] = useState('');
  const [githubUrl, setGithubUrl] = useState('');

  // Password form
  const [oldPw, setOldPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [showOld, setShowOld] = useState(false);
  const [showNew, setShowNew] = useState(false);

  useEffect(() => {
    usersApi.getProfile()
      .then((p: Profile) => {
        setProfile(p);
        setFullName(user?.full_name || '');
        setPhone(p.phone || '');
        setLocation(p.location || '');
        setJobTitle(p.job_title || '');
        setBio(p.bio || '');
        setLinkedinUrl(p.linkedin_url || '');
        setGithubUrl(p.github_url || '');
      })
      .catch(() => toast.error('Lỗi tải thông tin hồ sơ'))
      .finally(() => setLoading(false));
  }, []);

  const handleSaveProfile = async () => {
    if (!fullName.trim()) return toast.error('Họ tên không được để trống');
    setSaving(true);
    try {
      // Update full_name in users table
      const updatedUser = await usersApi.updateMe({ full_name: fullName });
      updateUser({ full_name: updatedUser.full_name });

      // Update profile fields
      await usersApi.updateProfile({ phone, location, job_title: jobTitle, bio, linkedin_url: linkedinUrl, github_url: githubUrl });
      toast.success('Cập nhật hồ sơ thành công!');
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Lỗi cập nhật hồ sơ');
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async () => {
    if (!oldPw || !newPw || !confirmPw) return toast.error('Vui lòng điền đầy đủ thông tin');
    if (newPw.length < 8) return toast.error('Mật khẩu mới phải có ít nhất 8 ký tự');
    if (newPw !== confirmPw) return toast.error('Mật khẩu xác nhận không khớp');

    setSaving(true);
    try {
      await usersApi.changePassword({ old_password: oldPw, new_password: newPw });
      toast.success('Đổi mật khẩu thành công!');
      setOldPw(''); setNewPw(''); setConfirmPw('');
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Lỗi đổi mật khẩu');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="settings-page animate-fade-in">
      <div className="settings-header">
        <h2 className="flex items-center gap-2">
          <Settings size={22} className="text-brand" />
          Cài đặt tài khoản
        </h2>
        <p className="text-secondary text-sm mt-1">Quản lý thông tin cá nhân và bảo mật tài khoản</p>
      </div>

      <div className="settings-layout">
        {/* Tab Navigation */}
        <nav className="settings-nav card">
          <button
            className={`settings-tab ${activeTab === 'profile' ? 'active' : ''}`}
            onClick={() => setActiveTab('profile')}
          >
            <User size={16} /> Hồ sơ cá nhân
          </button>
          <button
            className={`settings-tab ${activeTab === 'password' ? 'active' : ''}`}
            onClick={() => setActiveTab('password')}
          >
            <Lock size={16} /> Đổi mật khẩu
          </button>
        </nav>

        {/* Content */}
        <div className="settings-content card">
          {loading ? (
            <div className="flex justify-center p-10">
              <Loader2 className="animate-spin text-brand" size={28} />
            </div>
          ) : activeTab === 'profile' ? (
            <div className="settings-section">
              <div className="section-title">
                <User size={18} className="text-brand" />
                <h3>Thông tin cá nhân</h3>
              </div>

              {/* Avatar placeholder */}
              <div className="avatar-section mb-6">
                <div className="settings-avatar bg-brand">
                  {fullName.charAt(0).toUpperCase() || 'U'}
                </div>
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
                  <input
                    className="form-input"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Nguyễn Văn A"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Chức danh</label>
                  <input
                    className="form-input"
                    value={jobTitle}
                    onChange={(e) => setJobTitle(e.target.value)}
                    placeholder="Full-stack Developer"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Số điện thoại</label>
                  <input
                    className="form-input"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="0901234567"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Địa điểm</label>
                  <input
                    className="form-input"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    placeholder="Hà Nội, Việt Nam"
                  />
                </div>
                <div className="form-group form-group-full">
                  <label className="form-label">Giới thiệu bản thân</label>
                  <textarea
                    className="form-input form-textarea"
                    value={bio}
                    onChange={(e) => setBio(e.target.value)}
                    placeholder="Mô tả ngắn về bản thân, kinh nghiệm và mục tiêu nghề nghiệp..."
                    rows={3}
                  />
                </div>
              </div>

              <div className="section-title mt-6">
                <Globe size={18} className="text-brand" />
                <h3>Liên kết mạng xã hội</h3>
              </div>
              <div className="form-grid">
                <div className="form-group">
                  <label className="form-label">LinkedIn URL</label>
                  <input
                    className="form-input"
                    value={linkedinUrl}
                    onChange={(e) => setLinkedinUrl(e.target.value)}
                    placeholder="https://linkedin.com/in/yourprofile"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">GitHub URL</label>
                  <input
                    className="form-input"
                    value={githubUrl}
                    onChange={(e) => setGithubUrl(e.target.value)}
                    placeholder="https://github.com/yourusername"
                  />
                </div>
              </div>

              <div className="form-actions">
                <button className="btn btn-primary" onClick={handleSaveProfile} disabled={saving}>
                  {saving ? <Loader2 className="animate-spin" size={16} /> : <Save size={16} />}
                  Lưu thay đổi
                </button>
              </div>
            </div>
          ) : (
            <div className="settings-section">
              <div className="section-title">
                <Lock size={18} className="text-brand" />
                <h3>Đổi mật khẩu</h3>
              </div>
              <p className="text-secondary text-sm mb-6">
                Để bảo mật tài khoản, bạn cần nhập mật khẩu hiện tại trước khi đặt mật khẩu mới.
              </p>

              <div className="form-stack">
                <div className="form-group">
                  <label className="form-label">Mật khẩu hiện tại</label>
                  <div className="input-pw-wrap">
                    <input
                      className="form-input"
                      type={showOld ? 'text' : 'password'}
                      value={oldPw}
                      onChange={(e) => setOldPw(e.target.value)}
                      placeholder="••••••••"
                    />
                    <button type="button" className="pw-toggle" onClick={() => setShowOld(!showOld)}>
                      {showOld ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Mật khẩu mới <span className="text-muted">(tối thiểu 8 ký tự)</span></label>
                  <div className="input-pw-wrap">
                    <input
                      className="form-input"
                      type={showNew ? 'text' : 'password'}
                      value={newPw}
                      onChange={(e) => setNewPw(e.target.value)}
                      placeholder="••••••••"
                    />
                    <button type="button" className="pw-toggle" onClick={() => setShowNew(!showNew)}>
                      {showNew ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Xác nhận mật khẩu mới</label>
                  <input
                    className={`form-input ${confirmPw && confirmPw !== newPw ? 'input-error' : ''}`}
                    type="password"
                    value={confirmPw}
                    onChange={(e) => setConfirmPw(e.target.value)}
                    placeholder="••••••••"
                  />
                  {confirmPw && confirmPw !== newPw && (
                    <p className="input-hint text-danger">Mật khẩu xác nhận không khớp</p>
                  )}
                </div>
              </div>

              <div className="form-actions">
                <button
                  className="btn btn-primary"
                  onClick={handleChangePassword}
                  disabled={saving || !oldPw || !newPw || !confirmPw || newPw !== confirmPw}
                >
                  {saving ? <Loader2 className="animate-spin" size={16} /> : <Lock size={16} />}
                  Đổi mật khẩu
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
