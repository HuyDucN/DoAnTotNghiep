import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';

import AppLayout from './components/layout/AppLayout';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import CVPage from './pages/CVPage';
import SkillProfilePage from './pages/SkillProfilePage';
import JobsPage from './pages/JobsPage';

// We will create these pages next
const PlaceholderPage = ({ title }: { title: string }) => (
  <div className="card animate-fade-in flex items-center justify-center" style={{ height: '400px' }}>
    <h2 className="text-muted">{title} - Coming Soon</h2>
  </div>
);

function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" toastOptions={{
        style: {
          background: '#1c1c28',
          color: '#f1f1f8',
          border: '1px solid rgba(255,255,255,0.1)'
        }
      }} />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        
        <Route path="/" element={<AppLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="cv" element={<CVPage />} />
          <Route path="profile" element={<SkillProfilePage />} />
          <Route path="jobs" element={<JobsPage />} />
          <Route path="reports" element={<PlaceholderPage title="Skill Gap Reports" />} />
          <Route path="settings" element={<PlaceholderPage title="Settings" />} />
        </Route>
        
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
