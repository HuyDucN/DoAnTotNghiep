import { Component, lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';

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

function RoleRoute({ role, children }: { role: 'user' | 'admin'; children: ReactNode }) {
  const user = useAuthStore((state) => state.user);
  if (!user) return null;
  return user.role === role ? children : <Navigate to={user.role === 'admin' ? '/admin' : '/dashboard'} replace />;
}

function HomeRedirect() {
  const user = useAuthStore((state) => state.user);
  return <Navigate to={user?.role === 'admin' ? '/admin' : '/dashboard'} replace />;
}

function PageFallback() {
  return <div className="flex justify-center p-8 text-muted" role="status">Đang tải trang...</div>;
}

class RouteLoadErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
  state = { hasError: false };

  static getDerivedStateFromError(): { hasError: boolean } {
    return { hasError: true };
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <main className="flex justify-center p-8" role="alert">
        <div className="card" style={{ maxWidth: '32rem', textAlign: 'center', padding: '2rem' }}>
          <h2>Không thể tải trang</h2>
          <p className="text-muted mt-2">
            Kết nối có thể đã gián đoạn hoặc phiên bản giao diện vừa được cập nhật.
          </p>
          <button type="button" className="btn btn-primary mt-4" onClick={() => window.location.reload()}>
            Tải lại ứng dụng
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
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#ffffff',
            color: '#18243a',
            border: '1px solid #e2e7ef',
            borderRadius: '10px',
            fontSize: '0.9rem',
          },
          success: { iconTheme: { primary: '#15803d', secondary: '#ffffff' } },
          error:   { iconTheme: { primary: '#dc2626', secondary: '#ffffff' } },
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
          <Route path="dashboard" element={<RoleRoute role="user"><DashboardPage /></RoleRoute>} />
          <Route path="cv"        element={<RoleRoute role="user"><CVPage /></RoleRoute>} />
          <Route path="profile"   element={<RoleRoute role="user"><SkillProfilePage /></RoleRoute>} />
          <Route path="jobs"      element={<RoleRoute role="user"><JobsPage /></RoleRoute>} />
          <Route path="reports"   element={<RoleRoute role="user"><ReportsPage /></RoleRoute>} />
          <Route path="settings"  element={<SettingsPage />} />
          <Route path="admin"     element={<RoleRoute role="admin"><AdminPage /></RoleRoute>} />
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
