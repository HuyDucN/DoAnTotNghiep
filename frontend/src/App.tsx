import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';

import AppLayout from './components/layout/AppLayout';
import LoginPage from './pages/auth/LoginPage';
import RegisterPage from './pages/auth/RegisterPage';
import DashboardPage from './pages/dashboard/DashboardPage';
import CVPage from './pages/cv/CVPage';
import SkillProfilePage from './pages/profile/SkillProfilePage';
import JobsPage from './pages/jobs/JobsPage';
import ReportsPage from './pages/reports/ReportsPage';
import SettingsPage from './pages/settings/SettingsPage';
import ForgotPasswordPage from './pages/auth/ForgotPasswordPage';
import ResetPasswordPage from './pages/auth/ResetPasswordPage';
import AdminPage from './pages/admin/AdminPage';
import { useAuthStore } from './store/authStore';
import type { ReactNode } from 'react';

function RoleRoute({ role, children }: { role: 'user' | 'admin'; children: ReactNode }) {
  const user = useAuthStore((state) => state.user);
  if (!user) return null;
  return user.role === role ? children : <Navigate to={user.role === 'admin' ? '/admin' : '/dashboard'} replace />;
}

function HomeRedirect() {
  const user = useAuthStore((state) => state.user);
  return <Navigate to={user?.role === 'admin' ? '/admin' : '/dashboard'} replace />;
}

function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#1c1c28',
            color: '#f1f1f8',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '10px',
            fontSize: '0.9rem',
          },
          success: { iconTheme: { primary: '#10b981', secondary: '#1c1c28' } },
          error:   { iconTheme: { primary: '#ef4444', secondary: '#1c1c28' } },
        }}
      />
      <Routes>
        {/* Public routes */}
        <Route path="/login"    element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />

        {/* Protected routes — wrapped in AppLayout */}
        <Route path="/" element={<AppLayout />}>
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
    </BrowserRouter>
  );
}

export default App;
