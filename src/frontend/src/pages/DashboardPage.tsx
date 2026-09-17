import React from 'react';
import './Dashboard.css';

export default function DashboardPage() {
  return (
    <div className="dashboard-page animate-fade-in">
      <div className="overview-grid">
        <article className="mini-metric card">
          <div className="metric-header">
            <span className="metric-title text-info">CV đã phân tích</span>
            <div className="metric-icon bg-info-light text-info">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
            </div>
          </div>
          <div className="metric-value">1,248</div>
          <div className="metric-trend text-success">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>
            <span>+12.4% so với tháng trước</span>
          </div>
        </article>

        <article className="mini-metric card">
          <div className="metric-header">
            <span className="metric-title text-success">Khớp mạnh</span>
             <div className="metric-icon bg-success-light text-success">
               <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
             </div>
          </div>
          <div className="metric-value">74%</div>
          <div className="metric-trend text-muted">
            <span>325 ứng viên</span>
          </div>
        </article>

        <article className="mini-metric card">
          <div className="metric-header">
            <span className="metric-title text-warning">Khoảng cách kỹ năng</span>
            <div className="metric-icon bg-warning-light text-warning">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
            </div>
          </div>
          <div className="metric-value">18%</div>
           <div className="metric-trend text-muted">
            <span>Cần đào tạo thêm</span>
          </div>
        </article>

        <article className="mini-metric card">
          <div className="metric-header">
            <span className="metric-title text-brand">Điểm AI trung bình</span>
            <div className="metric-icon bg-brand-light text-brand">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
            </div>
          </div>
          <div className="metric-value">81.6</div>
           <div className="metric-trend text-muted">
            <span>Tất cả vị trí</span>
          </div>
        </article>
      </div>

      <div className="dashboard-grid">
        <div className="card chart-panel">
          <div className="panel-header">
            <h3>Xu hướng kỹ năng</h3>
            <span className="badge badge-neutral">6 tháng qua</span>
          </div>
          <div className="chart-placeholder">
             <div className="chart-bars">
                <div className="bar-group"><span className="bar" style={{height: '48%'}}></span><label>Jan</label></div>
                <div className="bar-group"><span className="bar" style={{height: '55%'}}></span><label>Feb</label></div>
                <div className="bar-group"><span className="bar" style={{height: '62%'}}></span><label>Mar</label></div>
                <div className="bar-group"><span className="bar" style={{height: '68%'}}></span><label>Apr</label></div>
                <div className="bar-group"><span className="bar" style={{height: '76%'}}></span><label>May</label></div>
                <div className="bar-group"><span className="bar" style={{height: '84%'}}></span><label>Jun</label></div>
              </div>
          </div>
        </div>

        <div className="card applicant-panel">
          <div className="panel-header">
            <h3>Ứng viên gần đây</h3>
            <span className="badge badge-neutral">Top 3</span>
          </div>
          <div className="applicant-list">
            <div className="applicant-item">
              <div className="avatar bg-brand">HN</div>
              <div className="applicant-info">
                <h4>Hoàng Nam</h4>
                <p>Data Analyst</p>
              </div>
              <div className="score text-success">82%</div>
            </div>
            <div className="applicant-item">
              <div className="avatar bg-info">LM</div>
              <div className="applicant-info">
                <h4>Lê Minh</h4>
                <p>AI Engineer</p>
              </div>
              <div className="score text-success">79%</div>
            </div>
            <div className="applicant-item">
              <div className="avatar bg-warning">QT</div>
              <div className="applicant-info">
                <h4>Quỳnh Trang</h4>
                <p>Business Analyst</p>
              </div>
              <div className="score text-warning">76%</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
