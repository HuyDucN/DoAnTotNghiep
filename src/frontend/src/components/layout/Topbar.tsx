import React from 'react';
import { useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { Bell, User } from 'lucide-react';
import './Layout.css';

export default function Topbar() {
  const user = useAuthStore((s) => s.user);
  const location = useLocation();

  const getPageTitle = () => {
    if (location.pathname.includes('/dashboard')) return { title: 'Tổng quan hệ thống', eyebrow: 'Dashboard' };
    if (location.pathname.includes('/cv')) return { title: 'Quản lý Hồ sơ & CV', eyebrow: 'Quản lý CV' };
    if (location.pathname.includes('/profile')) return { title: 'Hồ sơ kỹ năng cá nhân', eyebrow: 'Kỹ năng' };
    if (location.pathname.includes('/jobs')) return { title: 'Vị trí & So khớp CV', eyebrow: 'Việc làm' };
    if (location.pathname.includes('/reports')) return { title: 'Báo cáo khoảng cách kỹ năng', eyebrow: 'Báo cáo' };
    if (location.pathname.includes('/settings')) return { title: 'Cài đặt hệ thống', eyebrow: 'Cài đặt' };
    return { title: 'AI CV Skill Gap', eyebrow: 'Trang chủ' };
  };

  const { title, eyebrow } = getPageTitle();

  return (
    <header className="topbar">
      <div>
        <p className="eyebrow muted">{eyebrow}</p>
        <h2>{title}</h2>
      </div>
      
      <div className="topbar-actions flex items-center gap-4">
        <button className="icon-btn">
          <Bell size={20} />
          <span className="badge-indicator"></span>
        </button>
        <div className="user-profile">
          <div className="avatar bg-brand">{user?.full_name?.charAt(0).toUpperCase() || 'U'}</div>
          <div className="user-info">
            <strong>{user?.full_name}</strong>
            <span>{user?.role === 'admin' ? 'Quản trị viên' : 'Ứng viên'}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
