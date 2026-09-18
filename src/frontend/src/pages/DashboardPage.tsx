import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../store/authStore';
import { cvApi, jobsApi } from '../services/api';
import type { CV, SkillGapResult } from '../types';
import { FileText, Briefcase, TrendingUp, Star, ArrowRight, Loader2, CheckCircle, XCircle, Clock } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import './Dashboard.css';

interface DashboardStats {
  totalCvs: number;
  analyzedCvs: number;
  totalMatches: number;
  avgMatchScore: number;
  bestMatch: SkillGapResult | null;
  recentGaps: SkillGapResult[];
}

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats>({
    totalCvs: 0,
    analyzedCvs: 0,
    totalMatches: 0,
    avgMatchScore: 0,
    bestMatch: null,
    recentGaps: [],
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [cvsData, gapsData] = await Promise.all([
          cvApi.list(),
          jobsApi.getGapHistory(),
        ]);

        const cvs: CV[] = cvsData;
        const gaps: SkillGapResult[] = gapsData;

        const analyzedCvs = cvs.filter((c) => c.status === 'analyzed').length;
        const avgScore = gaps.length > 0
          ? Math.round(gaps.reduce((sum, g) => sum + g.match_score, 0) / gaps.length * 10) / 10
          : 0;
        const bestMatch = gaps.length > 0
          ? gaps.reduce((best, g) => g.match_score > best.match_score ? g : best, gaps[0])
          : null;

        setStats({
          totalCvs: cvs.length,
          analyzedCvs,
          totalMatches: gaps.length,
          avgMatchScore: avgScore,
          bestMatch,
          recentGaps: gaps.slice(0, 5),
        });
      } catch (e) {
        // Fail silently — dashboard is non-critical
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

  const getScoreColor = (score: number) => {
    if (score >= 75) return 'text-success';
    if (score >= 50) return 'text-warning';
    return 'text-danger';
  };

  const getScoreBadgeClass = (score: number) => {
    if (score >= 75) return 'badge-success';
    if (score >= 50) return 'badge-warning';
    return 'badge-danger';
  };

  const greetingHour = new Date().getHours();
  const greeting = greetingHour < 12 ? 'Chào buổi sáng' : greetingHour < 18 ? 'Chào buổi chiều' : 'Chào buổi tối';

  return (
    <div className="dashboard-page animate-fade-in">
      {/* Welcome Banner */}
      <div className="welcome-banner card">
        <div className="welcome-text">
          <h2>{greeting}, <span className="text-brand">{user?.full_name}</span> 👋</h2>
          <p className="text-secondary">
            {stats.analyzedCvs > 0
              ? `Bạn có ${stats.analyzedCvs} CV đã phân tích và ${stats.totalMatches} lần so khớp công việc.`
              : 'Tải lên CV đầu tiên của bạn để bắt đầu phân tích kỹ năng bằng AI.'}
          </p>
        </div>
        {stats.analyzedCvs === 0 && (
          <button className="btn btn-primary" onClick={() => navigate('/cv')}>
            Bắt đầu ngay <ArrowRight size={16} />
          </button>
        )}
      </div>

      {/* Metric Cards */}
      <div className="overview-grid">
        <article className="mini-metric card">
          <div className="metric-header">
            <span className="metric-title text-info">CV đã phân tích</span>
            <div className="metric-icon bg-info-light text-info">
              <FileText size={20} />
            </div>
          </div>
          {loading ? <div className="metric-value"><Loader2 className="animate-spin" size={28} /></div> : (
            <>
              <div className="metric-value">{stats.analyzedCvs}</div>
              <div className="metric-trend text-muted">
                <span>Tổng {stats.totalCvs} CV đã upload</span>
              </div>
            </>
          )}
        </article>

        <article className="mini-metric card">
          <div className="metric-header">
            <span className="metric-title text-success">Lần so khớp</span>
            <div className="metric-icon bg-success-light text-success">
              <Briefcase size={20} />
            </div>
          </div>
          {loading ? <div className="metric-value"><Loader2 className="animate-spin" size={28} /></div> : (
            <>
              <div className="metric-value">{stats.totalMatches}</div>
              <div className="metric-trend text-muted">
                <span>Với các vị trí công việc</span>
              </div>
            </>
          )}
        </article>

        <article className="mini-metric card">
          <div className="metric-header">
            <span className="metric-title text-warning">Điểm phù hợp TB</span>
            <div className="metric-icon bg-warning-light text-warning">
              <TrendingUp size={20} />
            </div>
          </div>
          {loading ? <div className="metric-value"><Loader2 className="animate-spin" size={28} /></div> : (
            <>
              <div className={`metric-value ${stats.avgMatchScore > 0 ? getScoreColor(stats.avgMatchScore) : ''}`}>
                {stats.avgMatchScore > 0 ? `${stats.avgMatchScore}%` : '—'}
              </div>
              <div className="metric-trend text-muted">
                <span>{stats.totalMatches > 0 ? 'Trung bình tất cả vị trí' : 'Chưa có dữ liệu'}</span>
              </div>
            </>
          )}
        </article>

        <article className="mini-metric card">
          <div className="metric-header">
            <span className="metric-title text-brand">Khớp cao nhất</span>
            <div className="metric-icon bg-brand-light text-brand">
              <Star size={20} />
            </div>
          </div>
          {loading ? <div className="metric-value"><Loader2 className="animate-spin" size={28} /></div> : (
            <>
              <div className={`metric-value ${stats.bestMatch ? getScoreColor(stats.bestMatch.match_score) : ''}`}>
                {stats.bestMatch ? `${stats.bestMatch.match_score}%` : '—'}
              </div>
              <div className="metric-trend text-muted">
                <span className="truncate" style={{ maxWidth: '140px', display: 'inline-block' }}>
                  {stats.bestMatch ? stats.bestMatch.job.title : 'Chưa có dữ liệu'}
                </span>
              </div>
            </>
          )}
        </article>
      </div>

      {/* Main Grid */}
      <div className="dashboard-grid">
        {/* Recent Skill Gap History */}
        <div className="card">
          <div className="panel-header">
            <h3>Lịch sử phân tích gần đây</h3>
            <button className="btn btn-ghost btn-sm" onClick={() => navigate('/reports')}>
              Xem tất cả <ArrowRight size={14} />
            </button>
          </div>

          {loading ? (
            <div className="flex justify-center p-8"><Loader2 className="animate-spin text-brand" size={24} /></div>
          ) : stats.recentGaps.length === 0 ? (
            <div className="empty-state" style={{ padding: '32px 0' }}>
              <Briefcase size={36} className="text-muted mb-3" />
              <p className="text-muted text-sm">Chưa có lịch sử so khớp. Hãy vào trang <strong>Vị trí & So khớp</strong> để bắt đầu.</p>
              <button className="btn btn-outline btn-sm mt-4" onClick={() => navigate('/jobs')}>
                Đến trang So khớp
              </button>
            </div>
          ) : (
            <div className="gap-history-list">
              {stats.recentGaps.map((gap) => (
                <div key={gap.id} className="gap-history-item">
                  <div className="gap-job-info">
                    <h4>{gap.job.title}</h4>
                    <span className="text-muted text-xs">
                      <Clock size={12} className="inline mr-1" />
                      {new Date(gap.created_at).toLocaleDateString('vi-VN')}
                    </span>
                  </div>
                  <div className="gap-score-area">
                    <div className={`score-pill ${getScoreBadgeClass(gap.match_score)}`}>
                      {gap.match_score}%
                    </div>
                    <div className="gap-skill-counts text-xs text-muted">
                      <span className="text-success">✓ {gap.matched_skills.length}</span>
                      <span className="text-danger mx-1">✗ {gap.missing_skills.length}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="card">
          <div className="panel-header">
            <h3>Thao tác nhanh</h3>
          </div>
          <div className="quick-actions">
            <button className="quick-action-btn" onClick={() => navigate('/cv')}>
              <div className="qa-icon bg-info-light text-info"><FileText size={20} /></div>
              <div>
                <strong>Upload CV</strong>
                <p className="text-muted text-xs">Tải lên và phân tích CV bằng AI</p>
              </div>
              <ArrowRight size={16} className="text-muted ml-auto" />
            </button>
            <button className="quick-action-btn" onClick={() => navigate('/jobs')}>
              <div className="qa-icon bg-success-light text-success"><Briefcase size={20} /></div>
              <div>
                <strong>So khớp công việc</strong>
                <p className="text-muted text-xs">Tính điểm phù hợp & Skill Gap</p>
              </div>
              <ArrowRight size={16} className="text-muted ml-auto" />
            </button>
            <button className="quick-action-btn" onClick={() => navigate('/profile')}>
              <div className="qa-icon bg-brand-light text-brand"><Star size={20} /></div>
              <div>
                <strong>Xem hồ sơ kỹ năng</strong>
                <p className="text-muted text-xs">Kỹ năng trích xuất từ CV</p>
              </div>
              <ArrowRight size={16} className="text-muted ml-auto" />
            </button>
            <button className="quick-action-btn" onClick={() => navigate('/reports')}>
              <div className="qa-icon bg-warning-light text-warning"><TrendingUp size={20} /></div>
              <div>
                <strong>Báo cáo kỹ năng</strong>
                <p className="text-muted text-xs">Xem chi tiết Skill Gap</p>
              </div>
              <ArrowRight size={16} className="text-muted ml-auto" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
