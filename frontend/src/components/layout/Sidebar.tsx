import { NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { LayoutDashboard, FileText, Target, Briefcase, ClipboardList, Settings, LogOut, ShieldCheck } from 'lucide-react';
import './Layout.css';

export default function Sidebar() {
  const logout = useAuthStore((s) => s.logout);
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();
  const signOut = () => { logout(); navigate('/login'); };
  const linkClass = ({ isActive }: { isActive: boolean }) => `nav-item ${isActive ? 'active' : ''}`;

  return <aside className="sidebar"><div><div className="brand"><div className="brand-mark"><ShieldCheck size={22} /></div><div><p className="eyebrow">HỆ THỐNG AI</p><h1>CV Skill Gap</h1></div></div>
    <nav className="nav" aria-label={user?.role === 'admin' ? 'Điều hướng quản trị' : 'Điều hướng ứng viên'}>
      {user?.role === 'admin' ? <><p className="nav-section-label">QUẢN TRỊ HỆ THỐNG</p><NavLink to="/admin" className={linkClass}><LayoutDashboard size={18} /> Trung tâm quản trị</NavLink><NavLink to="/settings" className={linkClass}><Settings size={18} /> Tài khoản quản trị</NavLink></> : <><p className="nav-section-label">KHÔNG GIAN ỨNG VIÊN</p><NavLink to="/dashboard" className={linkClass}><LayoutDashboard size={18} /> Tổng quan</NavLink><NavLink to="/cv" className={linkClass}><FileText size={18} /> CV của tôi</NavLink><NavLink to="/profile" className={linkClass}><Target size={18} /> Hồ sơ năng lực</NavLink><NavLink to="/jobs" className={linkClass}><Briefcase size={18} /> Việc làm phù hợp</NavLink><NavLink to="/reports" className={linkClass}><ClipboardList size={18} /> Báo cáo kỹ năng</NavLink><NavLink to="/settings" className={linkClass}><Settings size={18} /> Cài đặt tài khoản</NavLink></>}
    </nav></div><div><div className="mini-card mb-4"><p className="mini-label">Phiên đăng nhập</p><div className="status-row"><span className="status-dot" /><strong>{user?.role === 'admin' ? 'Quản trị viên' : 'Ứng viên'}</strong></div></div><button className="nav-item text-muted w-full" onClick={signOut}><LogOut size={18} /> Đăng xuất</button></div>
  </aside>;
}
