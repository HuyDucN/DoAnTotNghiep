import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { LayoutDashboard, FileText, Target, Briefcase, ClipboardList, Settings, LogOut, Bot } from 'lucide-react';
import './Layout.css';

export default function Sidebar() {
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <aside className="sidebar">
      <div>
        <div className="brand">
          <div className="brand-mark">
            <svg width="24" height="24" viewBox="0 0 28 28" fill="none">
              <rect width="28" height="28" rx="8" fill="url(#grad3)" />
              <path d="M8 14l4 4 8-8" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
              <defs>
                <linearGradient id="grad3" x1="0" y1="0" x2="28" y2="28">
                  <stop stopColor="#6366f1"/><stop offset="1" stopColor="#8b5cf6"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <div>
            <p className="eyebrow">Hệ thống AI</p>
            <h1>CV Skill Gap</h1>
          </div>
        </div>

        <nav className="nav">
          <NavLink to="/dashboard" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <LayoutDashboard size={18} /> Tổng quan
          </NavLink>
          <NavLink to="/cv" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <FileText size={18} /> Quản lý CV
          </NavLink>
          <NavLink to="/profile" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <Target size={18} /> Hồ sơ kỹ năng
          </NavLink>
          <NavLink to="/jobs" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <Briefcase size={18} /> Vị trí & So khớp
          </NavLink>
          <NavLink to="/reports" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <ClipboardList size={18} /> Báo cáo kỹ năng
          </NavLink>
          <NavLink to="/settings" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <Settings size={18} /> Cài đặt
          </NavLink>
        </nav>
      </div>

      <div>
        <div className="mini-card mb-4">
          <p className="mini-label">Trạng thái AI</p>
          <div className="status-row">
            <span className="status-dot"></span>
            <strong>Gemini 2.0 Trực tuyến</strong>
          </div>
        </div>
        <button className="nav-item text-muted w-full" onClick={handleLogout}>
          <LogOut size={18} /> Đăng xuất
        </button>
      </div>
    </aside>
  );
}
