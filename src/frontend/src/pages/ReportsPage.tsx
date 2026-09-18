import React, { useState, useEffect } from 'react';
import { jobsApi } from '../services/api';
import type { SkillGapResult } from '../types';
import {
  ClipboardList, Loader2, ChevronDown, ChevronUp,
  CheckCircle, XCircle, AlertTriangle, TrendingUp, Calendar
} from 'lucide-react';
import toast from 'react-hot-toast';
import './ReportsPage.css';

export default function ReportsPage() {
  const [gaps, setGaps] = useState<SkillGapResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  useEffect(() => {
    jobsApi.getGapHistory()
      .then(setGaps)
      .catch(() => toast.error('Lỗi tải lịch sử phân tích'))
      .finally(() => setLoading(false));
  }, []);

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
            Lịch sử toàn bộ lần phân tích khoảng cách kỹ năng của bạn.
          </p>
        </div>
        <span className="badge badge-neutral">{gaps.length} lần phân tích</span>
      </div>

      {gaps.length === 0 ? (
        <div className="card empty-reports">
          <ClipboardList size={52} className="text-muted mb-4" />
          <h3>Chưa có báo cáo nào</h3>
          <p className="text-muted">Hãy vào trang <strong>Vị trí &amp; So khớp</strong> để bắt đầu phân tích CV với một vị trí công việc.</p>
        </div>
      ) : (
        <div className="reports-list">
          {gaps.map((gap) => (
            <div key={gap.id} className="report-card card">
              {/* Header row — always visible */}
              <div className="report-row" onClick={() => toggle(gap.id)}>
                <div className="report-job">
                  <h4>{gap.job.title}</h4>
                  <span className="text-muted text-xs flex items-center gap-1">
                    <Calendar size={12} />
                    {new Date(gap.created_at).toLocaleDateString('vi-VN', {
                      day: '2-digit', month: '2-digit', year: 'numeric',
                      hour: '2-digit', minute: '2-digit',
                    })}
                  </span>
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

                <button className="expand-btn">
                  {expandedId === gap.id ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                </button>
              </div>

              {/* Expanded Detail */}
              {expandedId === gap.id && (
                <div className="report-detail animate-fade-in">
                  <div className="divider" />

                  <div className="skill-columns">
                    {/* Met skills */}
                    <div className="skill-col-report">
                      <h5 className="text-success flex items-center gap-2 mb-3">
                        <CheckCircle size={15} /> Kỹ năng đáp ứng ({gap.matched_skills.length})
                      </h5>
                      <div className="skill-tag-list">
                        {gap.matched_skills.map((s) => (
                          <span key={s.skill_id} className="skill-tag skill-tag-success">
                            {s.skill_name}
                            {s.is_required && <span className="tag-label">R</span>}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Missing skills */}
                    <div className="skill-col-report">
                      <h5 className="text-danger flex items-center gap-2 mb-3">
                        <XCircle size={15} /> Kỹ năng còn thiếu ({gap.missing_skills.length})
                      </h5>
                      <div className="skill-tag-list">
                        {gap.missing_skills.map((s) => (
                          <span key={s.skill_id} className={`skill-tag skill-tag-missing priority-${s.priority}`}>
                            {s.skill_name}
                            {s.is_required && <span className="tag-label">R</span>}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Weak skills */}
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

                  {/* AI Recommendation */}
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
      )}
    </div>
  );
}
