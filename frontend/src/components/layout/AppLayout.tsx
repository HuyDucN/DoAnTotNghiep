import { useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import CvAnalysisMonitor from '../CvAnalysisMonitor';
import './Layout.css';

export default function AppLayout() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const role = useAuthStore((s) => s.user?.role);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login', { state: { from: location.pathname } });
    }
  }, [isAuthenticated, navigate, location]);

  if (!isAuthenticated) return null;

  return (
    <div className="app-shell">
      {role === 'user' && <CvAnalysisMonitor />}
      <Sidebar />
      <main className="main-panel">
        <Topbar />
        <div className="page-content">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
