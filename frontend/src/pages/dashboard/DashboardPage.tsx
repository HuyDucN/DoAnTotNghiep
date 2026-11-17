import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../../store/authStore';
import { cvApi, jobsApi } from '../../services/api';
import type { CV, SkillGapResult } from '../../types';
import CvMatchStatusBadge from '../../components/CvMatchStatusBadge';
import QueryLoadNotice from '../../components/QueryLoadNotice';
import { FileText, Briefcase, TrendingUp, Star, ArrowRight, Loader2, Clock, Upload, Check, ArrowUpRight } from 'lucide-react';
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
  const journey = [
    { title: 'Thêm CV của bạn', description: 'Bắt đầu với hồ sơ hiện tại', to: '/cv', done: hasCvs ? stats.totalCvs > 0 : null },
    { title: 'Khám phá năng lực', description: 'Xem kỹ năng AI đã phân tích', to: '/profile', done: hasCvs ? stats.analyzedCvs > 0 : null },
    { title: 'Tìm cơ hội phù hợp', description: 'So khớp CV với công việc', to: '/jobs', done: hasGaps ? stats.totalMatches > 0 : null },
  ];
  const doneSteps = journey.filter((s) => s.done === true).length;
  const readiness = Math.round((doneSteps / journey.length) * 100);

  return (
    <div className="dashboard-page animate-fade-in">
      <section className="welcome-banner">
        <div className="welcome-text">
          <span className="hero-label">Hồ sơ ứng viên</span>
          <h2>{greeting}, {user?.full_name || 'bạn'}.</h2>
          <p className="text-secondary">
            {!hasCvs
              ? cvsQuery.isPending ? 'Đang tải thông tin CV của bạn...' : 'Chưa tải được thông tin CV của bạn. Vui lòng thử lại bên dưới.'
              : stats.analyzedCvs > 0
                ? `Bạn có ${stats.analyzedCvs} CV đã phân tích${hasGaps ? ` và ${stats.totalMatches} kết quả so khớp công việc` : ''}.`
                : stats.totalCvs > 0
                  ? 'Theo dõi trạng thái phân tích CV của bạn bên dưới.'
                  : cvsQuery.isSuccess ? 'Tải lên CV đầu tiên của bạn để bắt đầu phân tích kỹ năng bằng AI.' : 'Chưa xác nhận được danh sách CV mới nhất.'}
          </p>
          <div className="hero-actions">
            <button type="button" className="btn btn-primary" onClick={() => navigate('/cv')}><Upload size={16} aria-hidden="true" />Tải CV lên <ArrowRight size={15} aria-hidden="true" /></button>
            <button type="button" className="hero-secondary" onClick={() => navigate('/jobs')}>Khám phá việc làm <ArrowUpRight size={15} aria-hidden="true" /></button>
          </div>
          {stats.processingCvs > 0 && <p className="hero-processing"><Loader2 size={13} className="animate-spin" />{stats.processingCvs} CV đang được phân tích…</p>}
        </div>
        <div className="hero-readiness" aria-label="Muc do san sang">
          <div className="hero-readiness-top">
            <span>Mức độ sẵn sàng</span>
            <strong>{readiness}%</strong>
          </div>
          <div className="progress-bar" role="progressbar" aria-valuenow={readiness} aria-valuemin={0} aria-valuemax={100}>
            <div className="progress-bar-fill" style={{ width: `${readiness}%` }} />
          </div>
          <p>{doneSteps}/3 bước hoàn thành · {stats.totalMatches} lượt so khớp</p>
          <button type="button" className="hero-readiness-link" onClick={() => navigate(journey.find((s) => !s.done)?.to ?? '/jobs')}>
            Bước tiếp theo <ArrowUpRight size={14} aria-hidden="true" />
          </button>
        </div>
      </section>

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
                <span>Trong tổng số {stats.totalCvs} CV đã tải lên</span>
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
        <div className="card dashboard-history">
          <div className="panel-header">
            <div><span className="panel-kicker">HOẠT ĐỘNG CỦA BẠN</span><h3>So khớp gần đây</h3></div>
            <button className="btn btn-ghost btn-sm" onClick={() => navigate('/reports')}>
              Xem tất cả <ArrowRight size={14} />
            </button>
          </div>

          {gapsQuery.isPending ? (
            <div className="flex justify-center p-8"><Loader2 className="animate-spin text-brand" size={24} /></div>
          ) : (!hasGaps || (gapsQuery.isError && stats.recentGaps.length === 0)) ? (
            <p className="text-muted text-sm" role="status">Chưa tải được kết quả so khớp. Vui lòng thử tải lại ở thông báo phía trên.</p>
          ) : stats.recentGaps.length === 0 ? (
            <div className="dashboard-empty">
              <span className="dashboard-empty-icon"><Briefcase size={28} strokeWidth={1.5} aria-hidden="true" /></span>
              <h4>Cơ hội tiếp theo đang chờ bạn</h4>
              <p>So khớp CV với một công việc để biết điểm mạnh<br className="desktop-break" /> và những kỹ năng bạn có thể phát triển.</p>
              <button type="button" className="btn btn-secondary" onClick={() => navigate('/jobs')}>Tìm công việc phù hợp <ArrowRight size={14} aria-hidden="true" /></button>
            </div>
          ) : (
            <div className="gap-history-list">
              {stats.recentGaps.map((gap) => (
                <div key={gap.id} className="gap-history-item">
                  <span className="gap-company-mark" aria-hidden="true">{gap.job.title.charAt(0).toUpperCase()}</span>
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

        <aside className="dashboard-side">
        <div className="card journey-card">
          <span className="panel-kicker">TỪ HÔM NAY, TỪNG BƯỚC MỘT</span>
          <h3>Hành trình của bạn</h3>
          <div className="journey-steps">
            {journey.map((step, index) => (
              <button type="button" className={'journey-step' + (step.done ? ' is-complete' : '')} key={step.to} onClick={() => navigate(step.to)}>
                <span className="journey-number">{step.done ? <Check size={13} aria-hidden="true" /> : String(index + 1).padStart(2, '0')}</span>
                <span><strong>{step.title}</strong><small>{step.done === null ? 'Chưa tải được trạng thái' : step.done ? 'Đã hoàn thành' : step.description}</small></span>
                <ArrowUpRight size={14} className="journey-arrow" aria-hidden="true" />
              </button>
            ))}
          </div>
        </div>
        <div className="card quick-actions-card">
          <div className="panel-header">
            <h3>Lối tắt cho bạn</h3>
          </div>
          <div className="quick-actions">
            <button className="quick-action-btn" onClick={() => navigate('/cv')}>
              <div className="qa-icon bg-info-light text-info"><FileText size={20} /></div>
              <div>
                <strong>Quản lý CV</strong>
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
        </aside>
      </div>
      <footer className="dashboard-footer"><span>CV Skill Gap · Hiểu năng lực, chủ động tương lai.</span></footer>
    </div>
  );
}

