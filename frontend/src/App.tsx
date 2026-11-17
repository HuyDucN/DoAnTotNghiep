import { Component, lazy, Suspense, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AlertTriangle, Loader2, RefreshCw } from 'lucide-react';

import AppLayout from './components/layout/AppLayout';
import { useAuthStore } from './store/authStore';
import type { ReactNode } from 'react';

const LoginPage = lazy(() => import('./pages/auth/LoginPage'));
const RegisterPage = lazy(() => import('./pages/auth/RegisterPage'));
const DashboardPage = lazy(() => import('./pages/dashboard/DashboardPage'));
const CVPage = lazy(() => import('./pages/cv/CVPage'));
const SkillProfilePage = lazy(() => import('./pages/profile/SkillProfilePage'));
const JobsPage = lazy(() => import('./pages/jobs/JobsPage'));
const ReportsPage = lazy(() => import('./pages/reports/ReportsPage'));
const SettingsPage = lazy(() => import('./pages/settings/SettingsPage'));
const ForgotPasswordPage = lazy(() => import('./pages/auth/ForgotPasswordPage'));
const ResetPasswordPage = lazy(() => import('./pages/auth/ResetPasswordPage'));
const AdminPage = lazy(() => import('./pages/admin/AdminPage'));

function homeFor(role: string | undefined): string {
  if (role === 'admin') return '/admin';
  if (role === 'recruiter') return '/admin/jobs';
  return '/dashboard';
}

function RoleRoute({ roles, children }: { roles: Array<'user' | 'admin' | 'recruiter'>; children: ReactNode }) {
  const user = useAuthStore((state) => state.user);
  if (!user) return null;
  return roles.includes(user.role) ? children : <Navigate to={homeFor(user.role)} replace />;
}

function HomeRedirect() {
  const user = useAuthStore((state) => state.user);
  return <Navigate to={homeFor(user?.role)} replace />;
}

const routeTitles: Record<string, string> = {
  '/login': 'Đăng nhập',
  '/register': 'Tạo tài khoản',
  '/forgot-password': 'Quên mật khẩu',
  '/reset-password': 'Đặt lại mật khẩu',
  '/dashboard': 'Tổng quan',
  '/cv': 'CV của tôi',
  '/profile': 'Hồ sơ năng lực',
  '/jobs': 'Việc làm phù hợp',
  '/reports': 'Báo cáo kỹ năng',
  '/settings': 'Cài đặt tài khoản',
  '/admin': 'Trung tâm quản trị',
  '/admin/jobs': 'Quản lý Jobs',
  '/admin/skills': 'Quản lý Skills',
  '/admin/cvs': 'Quản lý CV',
  '/admin/users': 'Người dùng',
  '/admin/audit': 'Nhật ký kiểm toán',
};

function DocumentTitle() {
  const { pathname } = useLocation();

  useEffect(() => {
    const title = routeTitles[pathname] ?? 'CV Skill Gap';
    document.title = `${title} · CV Skill Gap`;
  }, [pathname]);

  return null;
}

function PageFallback() {
  return (
    <main className="route-state" role="status">
      <div className="route-state-card"><Loader2 size={22} className="animate-spin" /><span>Đang chuẩn bị trang của bạn...</span></div>
    </main>
  );
}

class RouteLoadErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
  state = { hasError: false };

  static getDerivedStateFromError(): { hasError: boolean } {
    return { hasError: true };
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <main className="route-state" role="alert">
        <div className="route-error-card">
          <span className="route-error-icon"><AlertTriangle size={20} aria-hidden="true" /></span>
          <h2>Không thể tải trang</h2>
          <p>
            Kết nối có thể đã gián đoạn hoặc phiên bản giao diện vừa được cập nhật.
          </p>
          <button type="button" className="btn btn-primary" onClick={() => window.location.reload()}>
            <RefreshCw size={14} aria-hidden="true" /> Tải lại ứng dụng
          </button>
        </div>
      </main>
    );
  }
}

function App() {
  const userId = useAuthStore((state) => state.user?.id);
  const sessionVersion = useAuthStore((state) => state.sessionVersion);
  return (
    <BrowserRouter>
      <DocumentTitle />
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#ffffff',
            color: '#212a3d',
            border: '1px solid #e5e2f2',
            borderRadius: '10px',
            fontSize: '0.78rem',
            boxShadow: '0 8px 24px rgba(42, 39, 75, 0.10)',
          },
          success: { iconTheme: { primary: '#287b62', secondary: '#ffffff' } },
          error:   { iconTheme: { primary: '#c55566', secondary: '#ffffff' } },
        }}
      />
      <RouteLoadErrorBoundary>
        <Suspense fallback={<PageFallback />}>
          <Routes>
        {/* Public routes */}
        <Route path="/login"    element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />

        {/* Protected routes — wrapped in AppLayout */}
        <Route path="/" element={<AppLayout key={`${userId ?? 'anonymous'}:${sessionVersion}`} />}>
          <Route index element={<HomeRedirect />} />
          <Route path="dashboard" element={<RoleRoute roles={['user']}><DashboardPage /></RoleRoute>} />
          <Route path="cv"        element={<RoleRoute roles={['user']}><CVPage /></RoleRoute>} />
          <Route path="profile"   element={<RoleRoute roles={['user']}><SkillProfilePage /></RoleRoute>} />
          <Route path="jobs"      element={<RoleRoute roles={['user']}><JobsPage /></RoleRoute>} />
          <Route path="reports"   element={<RoleRoute roles={['user']}><ReportsPage /></RoleRoute>} />
          <Route path="settings"  element={<SettingsPage />} />
          <Route path="admin"     element={<RoleRoute roles={['admin', 'recruiter']}><AdminPage /></RoleRoute>} />
          <Route path="admin/:section" element={<RoleRoute roles={['admin', 'recruiter']}><AdminPage /></RoleRoute>} />
        </Route>

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </RouteLoadErrorBoundary>
    </BrowserRouter>
  );
}

export default App;
