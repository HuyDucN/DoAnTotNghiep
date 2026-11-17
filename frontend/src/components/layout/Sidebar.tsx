import { NavLink, Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { LayoutDashboard, FileText, Target, Briefcase, ClipboardList, Settings, LogOut, Sparkles, ArrowUpRight, ChevronRight, Wrench, Users, ScrollText } from 'lucide-react';
import './Layout.css';

const candidateLinks = [
  { to: '/dashboard', label: 'Tổng quan', icon: LayoutDashboard },
  { to: '/cv', label: 'CV của tôi', icon: FileText },
  { to: '/profile', label: 'Hồ sơ năng lực', icon: Target },
  { to: '/jobs', label: 'Việc làm phù hợp', icon: Briefcase },
  { to: '/reports', label: 'Báo cáo kỹ năng', icon: ClipboardList },
];

const adminLinks = [
  { to: '/admin', label: 'Tổng quan', icon: LayoutDashboard },
  { to: '/admin/jobs', label: 'Quản lý Jobs', icon: Briefcase },
  { to: '/admin/skills', label: 'Quản lý Skills', icon: Wrench },
  { to: '/admin/cvs', label: 'Quản lý CV', icon: FileText },
  { to: '/admin/users', label: 'Người dùng', icon: Users },
  { to: '/admin/audit', label: 'Nhật ký', icon: ScrollText },
];

const recruiterLinks = [
  { to: '/admin/jobs', label: 'Tuyển dụng của tôi', icon: Briefcase },
];

export default function Sidebar() {
  const logout = useAuthStore((s) => s.logout);
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();
  const isAdmin = user?.role === 'admin';
  const isRecruiter = user?.role === 'recruiter';
  const homePath = isAdmin ? '/admin' : isRecruiter ? '/admin/jobs' : '/dashboard';
  const links = isAdmin ? adminLinks : isRecruiter ? recruiterLinks : candidateLinks;
  const workspaceLabel = isAdmin ? 'KHÔNG GIAN QUẢN TRỊ' : isRecruiter ? 'KHÔNG GIAN TUYỂN DỤNG' : 'KHÔNG GIAN CỦA BẠN';
  const navLabel = isAdmin ? 'Điều hướng quản trị' : isRecruiter ? 'Điều hướng tuyển dụng' : 'Điều hướng ứng viên';
  const roleLabel = isAdmin ? 'Quản trị viên' : isRecruiter ? 'Nhà tuyển dụng' : 'Tài khoản ứng viên';
  const guideTitle = isAdmin ? 'Không gian quản trị' : isRecruiter ? 'Không gian tuyển dụng' : 'Bước tiến nhỏ. Cơ hội lớn.';
  const guideText = isAdmin ? 'Quản lý dữ liệu để kết nối đúng người, đúng công việc.' : isRecruiter ? 'Đăng tin và theo dõi các vị trí của bạn.' : 'Bắt đầu từ CV để hiểu rõ kỹ năng và tìm hướng phát triển.';
  const guideLink = isAdmin ? '/admin' : isRecruiter ? '/admin/jobs' : '/cv';
  const guideLinkLabel = isAdmin ? 'Quản lý hệ thống' : isRecruiter ? 'Quản lý tin tuyển dụng' : 'Khám phá CV của bạn';
  const linkClass = ({ isActive }: { isActive: boolean }) => 'nav-item' + (isActive ? ' active' : '');

  return (
    <aside className="sidebar">
      <div className="sidebar-main">
        <Link to={homePath} className="brand" aria-label="CV Skill Gap — Trang chủ">
          <span className="brand-mark"><Sparkles size={23} aria-hidden="true" /></span>
          <span><strong className="brand-name">CV Skill Gap<span className="brand-period">.</span></strong><span className="brand-tagline">Hiểu năng lực. Mở cơ hội.</span></span>
        </Link>
        <p className="workspace-label">{workspaceLabel}</p>
        <nav className="nav" aria-label={navLabel}>
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === '/admin'} className={linkClass}>
              <Icon size={19} aria-hidden="true" /><span>{label}</span><ChevronRight size={14} className="nav-chevron" aria-hidden="true" />
            </NavLink>
          ))}
          <div className="nav-separator" />
          <NavLink to="/settings" className={linkClass}><Settings size={19} aria-hidden="true" /><span>Cài đặt tài khoản</span><ChevronRight size={14} className="nav-chevron" aria-hidden="true" /></NavLink>
        </nav>
      </div>
      <div className="sidebar-bottom">
        <div className="sidebar-guide">
          <span className="sidebar-guide-icon"><Sparkles size={19} aria-hidden="true" /></span>
          <strong>{guideTitle}</strong>
          <p>{guideText}</p>
          <Link to={guideLink}>{guideLinkLabel}<ArrowUpRight size={15} aria-hidden="true" /></Link>
        </div>
        <div className="sidebar-account">
          <span className="sidebar-avatar" aria-hidden="true">{user?.full_name?.charAt(0).toUpperCase() || 'U'}</span>
          <div className="sidebar-account-info"><strong title={user?.full_name}>{user?.full_name}</strong><span><i />{roleLabel}</span></div>
          <button type="button" className="sidebar-logout" onClick={() => { logout(); navigate('/login'); }} aria-label="Đăng xuất" title="Đăng xuất"><LogOut size={18} aria-hidden="true" /></button>
        </div>
      </div>
    </aside>
  );
}
