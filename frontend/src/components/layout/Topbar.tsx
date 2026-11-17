import { Link, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { CalendarDays, ChevronDown, ChevronRight, House, Settings } from 'lucide-react';
import './Layout.css';

const pageTitles: Record<string, string> = {
  '/admin': 'Trung tâm quản trị',
  '/admin/jobs': 'Quản lý Jobs',
  '/admin/skills': 'Quản lý Skills',
  '/admin/cvs': 'Quản lý CV',
  '/admin/users': 'Người dùng',
  '/admin/audit': 'Nhật ký kiểm toán',
  '/dashboard': 'Tổng quan',
  '/cv': 'CV của tôi',
  '/profile': 'Hồ sơ năng lực',
  '/jobs': 'Việc làm phù hợp',
  '/reports': 'Báo cáo kỹ năng',
  '/settings': 'Cài đặt tài khoản',
};

export default function Topbar() {
  const user = useAuthStore((s) => s.user);
  const { pathname } = useLocation();
  const title = pageTitles[pathname] ?? 'CV Skill Gap';
  const date = new Intl.DateTimeFormat('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(new Date());

  return (
    <header className="topbar">
      <nav className="topbar-breadcrumb" aria-label="Đường dẫn trang">
        <Link to={user?.role === 'admin' ? '/admin' : user?.role === 'recruiter' ? '/admin/jobs' : '/dashboard'} aria-label="Trang chủ"><House size={17} aria-hidden="true" /></Link>
        <ChevronRight size={14} aria-hidden="true" /><span aria-current="page">{title}</span>
      </nav>
      <div className="topbar-actions">
        <span className="topbar-date"><CalendarDays size={16} aria-hidden="true" />{date}</span>
        <Link to="/settings" className="icon-btn topbar-settings" aria-label="Cài đặt tài khoản" title="Cài đặt tài khoản"><Settings size={18} aria-hidden="true" /></Link>
        <Link to="/settings" className="user-profile" aria-label={'Tài khoản của ' + (user?.full_name ?? 'bạn')}>
          <span className="avatar bg-brand" aria-hidden="true">{user?.full_name?.charAt(0).toUpperCase() || 'U'}</span>
          <span className="user-info"><strong>{user?.full_name}</strong><span>{user?.role === 'admin' ? 'Quản trị viên' : user?.role === 'recruiter' ? 'Nhà tuyển dụng' : 'Ứng viên'}</span></span>
          <ChevronDown size={14} className="user-chevron" aria-hidden="true" />
        </Link>
      </div>
    </header>
  );
}
