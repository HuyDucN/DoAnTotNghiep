import React, { useState, useEffect } from 'react';
import { jobsApi, cvApi } from '../services/api';
import type { Job, CV, SkillGapResult } from '../types';
import { Briefcase, MapPin, DollarSign, Search, ChevronRight, Activity, ArrowRight, Loader2, CheckCircle, XCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import './JobsPage.css';

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [cvs, setCvs] = useState<CV[]>([]);
  const [selectedCvId, setSelectedCvId] = useState<number | ''>('');

  const [loadingJobs, setLoadingJobs] = useState(true);
  const [matching, setMatching] = useState(false);
  const [matchResult, setMatchResult] = useState<SkillGapResult | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [jobsData, cvsData] = await Promise.all([
          jobsApi.list(),
          cvApi.list()
        ]);
        setJobs(jobsData);
        setCvs(cvsData.filter((c: CV) => c.status === 'analyzed'));
        if (cvsData.length > 0) setSelectedCvId(cvsData[0].id);
      } catch (error) {
        toast.error('Lỗi tải dữ liệu');
      } finally {
        setLoadingJobs(false);
      }
    };
    fetchData();
  }, []);

  const handleMatch = async () => {
    if (!selectedJob || !selectedCvId) return toast.error('Vui lòng chọn CV và Job');

    setMatching(true);
    setMatchResult(null);
    try {
      const result = await jobsApi.match(selectedJob.id, Number(selectedCvId));
      setMatchResult(result);
      toast.success('So khớp thành công!');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Lỗi khi so khớp');
    } finally {
      setMatching(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-success';
    if (score >= 50) return 'text-warning';
    return 'text-danger';
  };

  return (
    <div className="jobs-page animate-fade-in">
      <div className="jobs-layout">
        {/* Left Column: Job List */}
        <div className="jobs-list-col">
          <div className="search-bar mb-4">
            <Search size={18} className="text-muted" />
            <input type="text" placeholder="Tìm kiếm vị trí..." className="search-input" />
          </div>

          {loadingJobs ? (
            <div className="flex justify-center p-8"><Loader2 className="animate-spin text-brand" size={24} /></div>
          ) : (
            <div className="job-cards">
              {jobs.map(job => (
                <div
                  key={job.id}
                  className={`job-card ${selectedJob?.id === job.id ? 'selected' : ''}`}
                  onClick={() => { setSelectedJob(job); setMatchResult(null); }}
                >
                  <div className="job-card-header">
                    <h4>{job.title}</h4>
                    <span className="badge badge-neutral">{job.level}</span>
                  </div>
                  <div className="job-card-meta">
                    <span className="flex items-center gap-1"><Briefcase size={14} /> {job.company || 'Ẩn danh'}</span>
                    <span className="flex items-center gap-1"><MapPin size={14} /> {job.location || 'Remote'}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Job Detail & Matching */}
        <div className="job-detail-col">
          {selectedJob ? (
            <div className="card job-detail-card">
              <div className="job-detail-header">
                <h2>{selectedJob.title}</h2>
                <div className="flex gap-3 mt-2 text-muted text-sm">
                  <span className="flex items-center gap-1"><Briefcase size={16} /> {selectedJob.company}</span>
                  <span className="flex items-center gap-1"><MapPin size={16} /> {selectedJob.location}</span>
                  {selectedJob.salary_min && (
                    <span className="flex items-center gap-1"><DollarSign size={16} /> {selectedJob.salary_min} - {selectedJob.salary_max} USD</span>
                  )}
                </div>
              </div>

              <div className="divider" />

              <div className="match-action-area">
                <div className="flex items-center gap-4">
                  <div className="form-group flex-1">
                    <label className="form-label">Chọn CV để so khớp</label>
                    <select
                      className="form-input"
                      value={selectedCvId}
                      onChange={(e) => setSelectedCvId(Number(e.target.value))}
                    >
                      <option value="">-- Chọn CV --</option>
                      {cvs.map(cv => (
                        <option key={cv.id} value={cv.id}>{cv.filename}</option>
                      ))}
                    </select>
                  </div>
                  <button
                    className="btn btn-primary"
                    style={{ marginTop: '24px' }}
                    onClick={handleMatch}
                    disabled={matching || !selectedCvId}
                  >
                    {matching ? <Loader2 className="animate-spin" size={18} /> : <Activity size={18} />}
                    Phân tích độ phù hợp
                  </button>
                </div>
              </div>

              {matchResult && (
                <div className="match-result-area animate-slide-in">
                  <div className="match-score-header">
                    <div className="score-ring-wrapper">
                      <svg width="80" height="80" viewBox="0 0 100 100">
                        <circle cx="50" cy="50" r="45" fill="none" stroke="var(--bg-border)" strokeWidth="8" />
                        <circle
                          cx="50" cy="50" r="45" fill="none"
                          stroke="currentColor" strokeWidth="8"
                          strokeDasharray={`${matchResult.match_score * 2.83} 283`}
                          className={getScoreColor(matchResult.match_score)}
                          strokeLinecap="round"
                          transform="rotate(-90 50 50)"
                        />
                      </svg>
                      <div className="score-ring-label">
                        <strong className={getScoreColor(matchResult.match_score)}>{matchResult.match_score}%</strong>
                        <span>Match</span>
                      </div>
                    </div>
                    <div>
                      <h3>Kết quả phân tích</h3>
                      <p className="text-muted text-sm">AI đã so khớp kỹ năng của bạn với yêu cầu công việc.</p>
                    </div>
                  </div>

                  <div className="skills-comparison">
                    <div className="skill-col">
                      <h4 className="text-success flex items-center gap-2 mb-3">
                        <CheckCircle size={16} /> Đã đáp ứng ({matchResult.matched_skills.length})
                      </h4>
                      <ul className="skill-list-simple">
                        {matchResult.matched_skills.map(s => (
                          <li key={s.skill_id}>
                            {s.skill_name} <span className="text-muted text-xs">({s.cv_level})</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="skill-col">
                      <h4 className="text-danger flex items-center gap-2 mb-3">
                        <XCircle size={16} /> Cần bổ sung ({matchResult.missing_skills.length})
                      </h4>
                      <ul className="skill-list-simple">
                        {matchResult.missing_skills.map(s => (
                          <li key={s.skill_id}>
                            {s.skill_name}
                            {s.is_required && <span className="badge badge-danger ml-2" style={{ padding: '1px 4px', fontSize: '10px' }}>Required</span>}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {matchResult.ai_recommendation && (
                    <div className="ai-recommendation mt-6">
                      <h4>💡 Lời khuyên từ AI Career Advisor</h4>
                      <div className="ai-rec-content">
                        {matchResult.ai_recommendation.split('\n').map((line, i) => (
                          <p key={i}>{line}</p>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {!matchResult && (
                <div className="job-description mt-6">
                  <h4>Mô tả công việc</h4>
                  <p className="text-secondary text-sm mt-2">{selectedJob.description}</p>

                  <h4 className="mt-6 mb-2">Kỹ năng yêu cầu</h4>
                  <div className="flex flex-wrap gap-2">
                    {selectedJob.job_skills.filter(s => s.is_required).map(s => (
                      <span key={s.skill_id} className="badge badge-primary">{s.skill_name}</span>
                    ))}
                  </div>

                  <h4 className="mt-6 mb-2">Kỹ năng ưu tiên (Plus)</h4>
                  <div className="flex flex-wrap gap-2">
                    {selectedJob.job_skills.filter(s => !s.is_required).map(s => (
                      <span key={s.skill_id} className="badge badge-neutral">{s.skill_name}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="empty-job-state flex flex-col items-center justify-center h-full text-muted">
              <Briefcase size={48} className="mb-4 opacity-50" />
              <h3>Chọn một công việc</h3>
              <p>Chọn công việc từ danh sách bên trái để xem chi tiết và so khớp CV</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
