import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../../store/authStore';
import { cvApi, jobsApi } from '../../services/api';
import type { CV, SkillGapResult } from '../../types';
import CvMatchStatusBadge from '../../components/CvMatchStatusBadge';
import QueryLoadNotice from '../../components/QueryLoadNotice';
import { FileText, Briefcase, TrendingUp, Star, ArrowRight, Loader2, Clock } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import './Dashboard.css';

interface DashboardStats {
  totalCvs: number;
  analyzedCvs: number;
  processingCvs: number;
  totalMatches: number;
  avgMatchScore: number;
  bestMatch: SkillGapResult | null;
  recentGaps: SkillGapResult[];
}

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();

  const cvsQuery = useQuery<CV[]>({
    queryKey: ['cvs', 'mine'],
    queryFn: () => cvApi.list(),
  });

  const gapsQuery = useQuery<SkillGapResult[]>({
    queryKey: ['skill-gaps', 'mine'],
    queryFn: () => jobsApi.getGapHistory(),
  });

  const hasCvs = cvsQuery.data !== undefined;
  const hasGaps = gapsQuery.data !== undefined;

  const stats = useMemo<DashboardStats>(() => {
    const cvs = cvsQuery.data ?? [];
    const gaps = gapsQuery.data ?? [];
    const analyzedCvs = cvs.filter((cv) => cv.status === 'analyzed').length;
    const processingCvs = cvs.filter(
      (cv) => cv.status === 'processing' || cv.status === 'uploaded',
    ).length;
    const avgScore = gaps.length > 0
      ? Math.round(gaps.reduce((sum, gap) => sum + gap.match_score, 0) / gaps.length * 10) / 10
      : 0;
    const bestMatch = gaps.length > 0
      ? gaps.reduce((best, gap) => gap.match_score > best.match_score ? gap : best, gaps[0])
      : null;

    return {
      totalCvs: cvs.length,
      analyzedCvs,
      processingCvs,
      totalMatches: gaps.length,
      avgMatchScore: avgScore,
      bestMatch,
      recentGaps: gaps.slice(0, 5),
    };
  }, [cvsQuery.data, gapsQuery.data]);

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
      <div className="welcome-banner card">
        <div className="welcome-text">
          <h2>{greeting}, <span className="text-brand">{user?.full_name}</span> 👋</h2>
          <p className="text-secondary">
            {!hasCvs
              ? cvsQuery.isPending ? 'Đang tải thông tin CV của bạn...' : 'Chưa tải được thông tin CV của bạn. Vui lòng thử lại bên dưới.'
              : stats.analyzedCvs > 0
                ? `Bạn có ${stats.analyzedCvs} CV đã phân tích${hasGaps ? ` và ${stats.totalMatches} kết quả so khớp công việc` : ''}.`
                : stats.totalCvs > 0
                  ? 'Theo dõi trạng thái phân tích CV của bạn bên dưới.'
                  : cvsQuery.isSuccess ? 'Tải lên CV đầu tiên của bạn để bắt đầu phân tích kỹ năng bằng AI.' : 'Chưa xác nhận được danh sách CV mới nhất.'}
          </p>
          {stats.processingCvs > 0 && (
            <p className="text-warning" style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>
              ⏳ {stats.processingCvs} CV đang được AI phân tích, vui lòng đợi vài phút...
            </p>
          )}
        </div>
        {cvsQuery.isSuccess && stats.totalCvs === 0 && (
          <button className="btn btn-primary" onClick={() => navigate('/cv')}>
            Bắt đầu ngay <ArrowRight size={16} />
          </button>
        )}
      </div>

      <QueryLoadNotice query={cvsQuery} label="danh sách CV" />
      <QueryLoadNotice query={gapsQuery} label="kết quả so khớp" />

      <div className="overview-grid">
        <article className="mini-metric card">
          <div className="metric-header">
            <span className="metric-title text-info">CV đã phân tích</span>
            <div className="metric-icon bg-info-light text-info">
              <FileText size={20} />
            </div>
          </div>
          {cvsQuery.isPending ? <div className="metric-value"><Loader2 className="animate-spin" size={28} /></div> : !hasCvs ? (
            <><div className="metric-value">—</div><p className="text-muted text-xs">Chưa tải được danh sách CV</p></>
          ) : (
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
            <span className="metric-title text-success">Kết quả so khớp</span>
            <div className="metric-icon bg-success-light text-success">
              <Briefcase size={20} />
            </div>
          </div>
          {gapsQuery.isPending ? <div className="metric-value"><Loader2 className="animate-spin" size={28} /></div> : !hasGaps ? (
            <><div className="metric-value">—</div><p className="text-muted text-xs">Chưa tải được kết quả</p></>
          ) : (
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
          {gapsQuery.isPending ? <div className="metric-value"><Loader2 className="animate-spin" size={28} /></div> : !hasGaps ? (
            <><div className="metric-value">—</div><p className="text-muted text-xs">Chưa tải được kết quả</p></>
          ) : (
            <>
              <div className={`metric-value ${stats.totalMatches > 0 ? getScoreColor(stats.avgMatchScore) : ''}`}>
                {stats.totalMatches > 0 ? `${stats.avgMatchScore}%` : '—'}
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
          {gapsQuery.isPending ? <div className="metric-value"><Loader2 className="animate-spin" size={28} /></div> : !hasGaps ? (
            <><div className="metric-value">—</div><p className="text-muted text-xs">Chưa tải được kết quả</p></>
          ) : (
            <>
              <div className={`metric-value ${stats.bestMatch ? getScoreColor(stats.bestMatch.match_score) : ''}`}>
                {stats.bestMatch ? `${stats.bestMatch.match_score}%` : '—'}
              </div>
              <div className="metric-trend text-muted">
                <span className="truncate" style={{ maxWidth: '140px', display: 'inline-block' }}>
                  {stats.bestMatch ? stats.bestMatch.job.title : 'Chưa có dữ liệu'}
                </span>
                {stats.bestMatch && !stats.bestMatch.job_snapshot_available && (
                  <span className="text-xs"> · Thông tin công việc hiện tại</span>
                )}
              </div>
              {stats.bestMatch && (
                <>
                  <p className="text-muted text-xs truncate" title={`CV #${stats.bestMatch.cv_id} · ${stats.bestMatch.cv_filename}`}>
                    CV #{stats.bestMatch.cv_id} · {stats.bestMatch.cv_filename}
                  </p>
                  <CvMatchStatusBadge status={gapsQuery.isError ? 'unknown' : stats.bestMatch.cv_match_status} />
                </>
              )}
            </>
          )}
        </article>
      </div>

      <div className="dashboard-grid">
        <div className="card">
          <div className="panel-header">
            <h3>Kết quả so khớp gần đây</h3>
            <button className="btn btn-ghost btn-sm" onClick={() => navigate('/reports')}>
              Xem tất cả <ArrowRight size={14} />
            </button>
          </div>

          {gapsQuery.isPending ? (
            <div className="flex justify-center p-8"><Loader2 className="animate-spin text-brand" size={24} /></div>
          ) : (!hasGaps || (gapsQuery.isError && stats.recentGaps.length === 0)) ? (
            <p className="text-muted text-sm" role="status">Chưa tải được kết quả so khớp. Vui lòng thử tải lại ở thông báo phía trên.</p>
          ) : stats.recentGaps.length === 0 ? (
            <div className="empty-state" style={{ padding: '32px 0' }}>
              <Briefcase size={36} className="text-muted mb-3" />
              <p className="text-muted text-sm">Chưa có lịch sử so khớp. Hãy vào trang <strong>Vị trí &amp; So khớp</strong> để bắt đầu.</p>
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
                    <p className="text-muted text-xs truncate" title={`CV #${gap.cv_id} · ${gap.cv_filename}`}>
                      CV #{gap.cv_id} · {gap.cv_filename}
                    </p>
                    <span className="text-muted text-xs">
                      <Clock size={12} className="inline mr-1" />
                      {gap.matched_at ? 'So khớp: ' : 'Tạo bản ghi: '}
                      {new Date(gap.matched_at ?? gap.created_at).toLocaleDateString('vi-VN')}
                      {!gap.job_snapshot_available && ' · Thông tin công việc hiện tại'}
                    </span>
                    <CvMatchStatusBadge status={gapsQuery.isError ? 'unknown' : gap.cv_match_status} />
                  </div>
                  <div className="gap-score-area">
                    <div className={`score-pill ${getScoreBadgeClass(gap.match_score)}`}>
                      {gap.match_score}%
                    </div>
                    <div className="gap-skill-counts text-xs text-muted">
                      <span className="text-success">✓ {gap.matched_skills.length}</span>
                      <span className="text-danger mx-1">✕ {gap.missing_skills.length}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

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
                <p className="text-muted text-xs">Tính điểm phù hợp &amp; Skill Gap</p>
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

