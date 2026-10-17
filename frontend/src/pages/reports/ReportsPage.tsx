import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { jobsApi } from '../../services/api';
import type { SkillGapResult } from '../../types';
import CvMatchStatusBadge from '../../components/CvMatchStatusBadge';
import QueryLoadNotice from '../../components/QueryLoadNotice';
import {
  ClipboardList, Loader2, ChevronDown, ChevronUp,
  CheckCircle, XCircle, AlertTriangle, TrendingUp, Calendar
} from 'lucide-react';
import './ReportsPage.css';

export default function ReportsPage() {
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const gapsQuery = useQuery<SkillGapResult[]>({
    queryKey: ['skill-gaps', 'mine'],
    queryFn: () => jobsApi.getGapHistory(),
  });
  const gaps = gapsQuery.data ?? [];
  const loading = gapsQuery.isPending;

  const getScoreColor = (score: number) => {
    if (score >= 75) return 'text-success';
    if (score >= 50) return 'text-warning';
    return 'text-danger';
  };

  const getScoreBg = (score: number) => {
    if (score >= 75) return 'score-bg-success';
    if (score >= 50) return 'score-bg-warning';
    return 'score-bg-danger';
  };

  const toggle = (id: number) =>
    setExpandedId((prev) => (prev === id ? null : id));

  const handleReportKeyDown = (event: React.KeyboardEvent<HTMLDivElement>, id: number) => {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    event.preventDefault();
    toggle(id);
  };

  if (loading) {
    return (
      <div className="flex justify-center mt-10">
        <Loader2 className="animate-spin text-brand" size={32} />
      </div>
    );
  }

  return (
    <div className="reports-page animate-fade-in">
      <div className="reports-header">
        <div>
          <h2 className="flex items-center gap-2">
            <ClipboardList size={24} className="text-brand" />
            Báo cáo Skill Gap
          </h2>
          <p className="text-secondary text-sm mt-1">
            Kết quả so khớp gần nhất theo từng CV và công việc.
          </p>
        </div>
        <span className="badge badge-neutral">{gapsQuery.data !== undefined ? `${gaps.length} kết quả` : '—'}</span>
      </div>

      <QueryLoadNotice query={gapsQuery} label="báo cáo" />

      {gapsQuery.isSuccess && gaps.length === 0 ? (
        <div className="card empty-reports">
          <ClipboardList size={52} className="text-muted mb-4" />
          <h3>Chưa có báo cáo nào</h3>
          <p className="text-muted">Hãy vào trang <strong>Vị trí &amp; So khớp</strong> để bắt đầu phân tích CV với một vị trí công việc.</p>
        </div>
      ) : gaps.length > 0 ? (
        <div className="reports-list">
          {gaps.map((gap) => (
            <div key={gap.id} className="report-card card">
              <div
                className="report-row"
                role="button"
                tabIndex={0}
                aria-expanded={expandedId === gap.id}
                aria-controls={`report-detail-${gap.id}`}
                onClick={() => toggle(gap.id)}
                onKeyDown={(event) => handleReportKeyDown(event, gap.id)}
              >
                <div className="report-job">
                  <h4>{gap.job.title}</h4>
                  <p className="text-muted text-xs truncate" title={`CV #${gap.cv_id} · ${gap.cv_filename}`}>
                    CV #{gap.cv_id} · {gap.cv_filename}
                  </p>
                  <span className="text-muted text-xs flex items-center gap-1">
                    <Calendar size={12} />
                    {gap.matched_at ? 'So khớp lúc' : 'Ngày tạo bản ghi'}{' '}
                    {new Date(gap.matched_at ?? gap.created_at).toLocaleDateString('vi-VN', {
                      day: '2-digit', month: '2-digit', year: 'numeric',
                      hour: '2-digit', minute: '2-digit',
                    })}
                  </span>
                  <CvMatchStatusBadge status={gapsQuery.isError ? 'unknown' : gap.cv_match_status} detailed />
                  <p className="text-muted text-xs mt-1">
                    {gap.job_snapshot_available
                      ? 'Thông tin công việc tại thời điểm so khớp.'
                      : 'Không có thông tin công việc tại thời điểm so khớp; đang hiển thị thông tin hiện tại.'}
                  </p>
                </div>

                <div className="report-summary">
                  <div className={`report-score-ring ${getScoreBg(gap.match_score)}`}>
                    <strong className={getScoreColor(gap.match_score)}>{gap.match_score}%</strong>
                    <span>Match</span>
                  </div>
                  <div className="skill-counts">
                    <div className="skill-count-item">
                      <CheckCircle size={14} className="text-success" />
                      <span>{gap.matched_skills.length} đạt</span>
                    </div>
                    <div className="skill-count-item">
                      <XCircle size={14} className="text-danger" />
                      <span>{gap.missing_skills.length} thiếu</span>
                    </div>
                    {gap.weak_skills.length > 0 && (
                      <div className="skill-count-item">
                        <AlertTriangle size={14} className="text-warning" />
                        <span>{gap.weak_skills.length} yếu</span>
                      </div>
                    )}
                  </div>
                </div>

                <span className="expand-btn" aria-hidden="true">
                  {expandedId === gap.id ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                </span>
              </div>

              {expandedId === gap.id && (
                <div id={`report-detail-${gap.id}`} className="report-detail animate-fade-in">
                  <div className="divider" />

                  <div className="skill-columns">
                    <div className="skill-col-report">
                      <h5 className="text-success flex items-center gap-2 mb-3">
                        <CheckCircle size={15} /> Kỹ năng đáp ứng ({gap.matched_skills.length})
                      </h5>
                      <div className="skill-tag-list">
                        {gap.matched_skills.map((s) => (
                          <span key={s.skill_id} className="skill-tag skill-tag-success">
                            {s.skill_name}
                            {s.is_required && <span className="tag-label">Bắt buộc</span>}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="skill-col-report">
                      <h5 className="text-danger flex items-center gap-2 mb-3">
                        <XCircle size={15} /> Kỹ năng còn thiếu ({gap.missing_skills.length})
                      </h5>
                      <div className="skill-tag-list">
                        {gap.missing_skills.map((s) => (
                          <span
                            key={s.skill_id}
                            className={`skill-tag skill-tag-missing priority-${s.priority}`}
                          >
                            {s.skill_name}
                            {s.is_required && <span className="tag-label">Bắt buộc</span>}
                          </span>
                        ))}
                      </div>
                    </div>

                    {gap.weak_skills.length > 0 && (
                      <div className="skill-col-report">
                        <h5 className="text-warning flex items-center gap-2 mb-3">
                          <AlertTriangle size={15} /> Kỹ năng cần nâng cao ({gap.weak_skills.length})
                        </h5>
                        <div className="skill-tag-list">
                          {gap.weak_skills.map((s) => (
                            <span key={s.skill_id} className="skill-tag skill-tag-weak">
                              {s.skill_name}
                              <span className="tag-label">{s.current_level} → {s.needed_level}</span>
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {gap.ai_recommendation && (
                    <div className="ai-rec-block mt-6">
                      <h5 className="flex items-center gap-2 mb-3">
                        <TrendingUp size={16} className="text-brand" />
                        💡 Lời khuyên từ AI Career Advisor
                      </h5>
                      <div className="ai-rec-text">
                        {gap.ai_recommendation.split('\n').filter(Boolean).map((line, i) => (
                          <p key={i}>{line}</p>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

