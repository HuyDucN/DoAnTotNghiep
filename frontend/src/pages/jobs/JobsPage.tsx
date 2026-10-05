import { useState, useEffect, useMemo } from 'react';
import { jobsApi, cvApi } from '../../services/api';
import type { Job, CV, SkillGapResult } from '../../types';
import {
  Briefcase, MapPin, DollarSign, Search,
  Activity, Loader2, CheckCircle, XCircle,
  AlertTriangle, Filter, ChevronDown,
} from 'lucide-react';
import toast from 'react-hot-toast';
import './JobsPage.css';

// Sửa nội dung giao diện để dùng tiếng Việt chuẩn.

// Helpers
const LEVEL_LABELS: Record<string, string> = {
  intern: 'Intern',
  fresher: 'Fresher',
  junior: 'Junior',
  mid: 'Mid-level',
  senior: 'Senior',
  lead: 'Lead',
};

function getScoreColor(score: number) {
  if (score >= 75) return 'text-success';
  if (score >= 50) return 'text-warning';
  return 'text-danger';
}
function formatSalary(min?: number, max?: number) {
  if (!min && !max) return null;
  if (min && max) return `${min.toLocaleString()} – ${max.toLocaleString()} USD`;
  return `${(min || max)!.toLocaleString()} USD`;
}

// Main component
export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [cvs, setCvs] = useState<CV[]>([]);
  const [selectedCvId, setSelectedCvId] = useState<number | ''>('');
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [matching, setMatching] = useState(false);
  const [matchResult, setMatchResult] = useState<SkillGapResult | null>(null);

  const [search, setSearch] = useState('');
  const [filterLevel, setFilterLevel] = useState('');

  // Fetch data
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [jobsData, cvsData] = await Promise.all([
          jobsApi.list(),
          cvApi.list(),
        ]);
        setJobs(jobsData);

        // Chỉ cho phép chọn CV đã được phân tích
        const analyzedCvs: CV[] = cvsData.filter((c: CV) => c.status === 'analyzed');
        setCvs(analyzedCvs);
        if (analyzedCvs.length > 0) setSelectedCvId(analyzedCvs[0].id);
      } catch {
        toast.error('Không thể tải dữ liệu. Kiểm tra kết nối server.');
      } finally {
        setLoadingJobs(false);
      }
    };
    fetchData();
  }, []);

  // Filtered jobs (search + level)
  const filteredJobs = useMemo(() => {
    let result = jobs;
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (j) =>
          j.title.toLowerCase().includes(q) ||
          (j.company ?? '').toLowerCase().includes(q),
      );
    }
    if (filterLevel) {
      result = result.filter((j) => j.level === filterLevel);
    }
    return result;
  }, [jobs, search, filterLevel]);

  // Match CV with Job
  const handleMatch = async () => {
    if (!selectedJob) return toast.error('Vui lòng chọn một công việc.');
    if (!selectedCvId) return toast.error('Vui lòng chọn CV đã phân tích.');

    setMatching(true);
    setMatchResult(null);
    try {
      const result = await jobsApi.match(selectedJob.id, Number(selectedCvId));
      setMatchResult(result);
      toast.success('So khớp thành công!');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Lỗi khi so khớp. Thử lại.');
    } finally {
      setMatching(false);
    }
  };

  // Render
  return (
    <div className="jobs-page animate-fade-in">
      <div className="jobs-layout">

        {/* Left: Job List */}
        <div className="jobs-list-col">
          {/* Search */}
          <div className="search-bar mb-4">
            <Search size={16} className="text-muted" />
            <input
              type="text"
              placeholder="Tìm kiếm vị trí, công ty..."
              className="search-input"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          {/* Level filter */}
          <div className="filter-bar mb-4">
            <Filter size={14} className="text-muted" />
            <select
              className="filter-select"
              value={filterLevel}
              onChange={(e) => setFilterLevel(e.target.value)}
            >
              <option value="">Tất cả cấp độ</option>
              {Object.entries(LEVEL_LABELS).map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </select>
            <ChevronDown size={13} className="text-muted" />
          </div>

          {/* Jobs count */}
          <p className="jobs-count text-muted text-xs mb-4">
            {loadingJobs ? '...' : `${filteredJobs.length} vị trí`}
          </p>

          {loadingJobs ? (
            <div className="flex justify-center p-8">
              <Loader2 className="animate-spin text-brand" size={24} />
            </div>
          ) : filteredJobs.length === 0 ? (
            <div className="empty-state" style={{ minHeight: '200px' }}>
              <Briefcase size={36} className="text-muted" />
              <p className="text-muted text-sm">
                {jobs.length === 0 ? 'Chưa có vị trí nào được đăng.' : 'Không tìm thấy vị trí phù hợp.'}
              </p>
            </div>
          ) : (
            <div className="job-cards">
              {filteredJobs.map((job) => (
                <div
                  key={job.id}
                  className={`job-card${selectedJob?.id === job.id ? ' selected' : ''}`}
                  onClick={() => { setSelectedJob(job); setMatchResult(null); }}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === 'Enter' && setSelectedJob(job)}
                >
                  <div className="job-card-header">
                    <h4>{job.title}</h4>
                    <span className="badge badge-neutral">{LEVEL_LABELS[job.level] ?? job.level}</span>
                  </div>
                  <div className="job-card-meta">
                    <span><Briefcase size={13} /> {job.company || 'Ẩn danh'}</span>
                    <span><MapPin size={13} /> {job.location || 'Remote'}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right: Job Detail & Matching */}
        <div className="job-detail-col">
          {selectedJob ? (
            <div className="card job-detail-card">

              {/* Job title & meta */}
              <div className="job-detail-header">
                <h2>{selectedJob.title}</h2>
                <div className="job-meta-row">
                  {selectedJob.company && (
                    <span><Briefcase size={15} /> {selectedJob.company}</span>
                  )}
                  {selectedJob.location && (
                    <span><MapPin size={15} /> {selectedJob.location}</span>
                  )}
                  {formatSalary(selectedJob.salary_min, selectedJob.salary_max) && (
                    <span>
                      <DollarSign size={15} />
                      {formatSalary(selectedJob.salary_min, selectedJob.salary_max)}
                    </span>
                  )}
                  <span className="badge badge-neutral">{LEVEL_LABELS[selectedJob.level] ?? selectedJob.level}</span>
                </div>
              </div>

              <div className="divider" />

              {/* Match action */}
              <div className="match-action-area">
                <p className="text-sm text-secondary" style={{ marginBottom: '0.75rem' }}>
                  Chọn CV đã phân tích để AI tính điểm phù hợp với vị trí này:
                </p>
                <div className="match-controls">
                  <div className="form-group flex-1" style={{ marginBottom: 0 }}>
                    <label className="form-label">CV của bạn</label>
                    {cvs.length === 0 ? (
                      <p className="text-warning text-sm">
                        ⚠ Bạn chưa có CV nào được phân tích. Hãy tải CV lên ở trang <strong>CV của tôi</strong>.
                      </p>
                    ) : (
                      <select
                        className="form-input"
                        value={selectedCvId}
                        onChange={(e) => setSelectedCvId(Number(e.target.value))}
                      >
                        {cvs.map((cv) => (
                          <option key={cv.id} value={cv.id}>{cv.filename}</option>
                        ))}
                      </select>
                    )}
                  </div>
                  <button
                    className="btn btn-primary match-btn"
                    onClick={handleMatch}
                    disabled={matching || !selectedCvId || cvs.length === 0}
                  >
                    {matching
                      ? <><Loader2 className="animate-spin" size={16} /> Đang phân tích...</>
                      : <><Activity size={16} /> Phân tích độ phù hợp</>
                    }
                  </button>
                </div>
              </div>

              {/* Match result */}
              {matchResult && (
                <div className="match-result-area animate-fade-in">
                  {/* Score header */}
                  <div className="match-score-header">
                    <div className="score-ring-wrapper">
                      <svg width="90" height="90" viewBox="0 0 100 100">
                        <circle cx="50" cy="50" r="42" fill="none" stroke="var(--bg-border)" strokeWidth="8" />
                        <circle
                          cx="50" cy="50" r="42" fill="none"
                          stroke="currentColor" strokeWidth="8"
                          strokeDasharray={`${matchResult.match_score * 2.64} 264`}
                          className={getScoreColor(matchResult.match_score)}
                          strokeLinecap="round"
                          transform="rotate(-90 50 50)"
                        />
                      </svg>
                      <div className="score-ring-label">
                        <strong className={getScoreColor(matchResult.match_score)}>
                          {matchResult.match_score}%
                        </strong>
                        <span>Match</span>
                      </div>
                    </div>
                    <div>
                      <h3>Kết quả phân tích</h3>
                      <p className="text-muted text-sm" style={{ marginTop: '0.25rem' }}>
                        AI đã so sánh kỹ năng CV của bạn với yêu cầu vị trí <strong>{selectedJob.title}</strong>.
                      </p>
                      {/* Summary pills */}
                      <div className="score-pills">
                        <span className="score-pill-item success">
                          <CheckCircle size={13} /> {matchResult.matched_skills.length} kỹ năng đáp ứng
                        </span>
                        {matchResult.weak_skills.length > 0 && (
                          <span className="score-pill-item warning">
                            <AlertTriangle size={13} /> {matchResult.weak_skills.length} cần nâng cao
                          </span>
                        )}
                        <span className="score-pill-item danger">
                          <XCircle size={13} /> {matchResult.missing_skills.length} còn thiếu
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Skills comparison - 3 columns */}
                  <div className="skills-comparison">
                    {/* Matched */}
                    <div className="skill-col">
                      <h4 className="skill-col-title text-success">
                        <CheckCircle size={15} /> Đã đáp ứng ({matchResult.matched_skills.length})
                      </h4>
                      {matchResult.matched_skills.length === 0 ? (
                        <p className="text-muted text-xs">Không có kỹ năng nào khớp.</p>
                      ) : (
                        <ul className="skill-list-simple">
                          {matchResult.matched_skills.map((s) => (
                            <li key={s.skill_id}>
                              <span>{s.skill_name}</span>
                              <span className="badge badge-success text-xs">{s.cv_level}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>

                    {/* Weak */}
                    <div className="skill-col">
                      <h4 className="skill-col-title text-warning">
                        <AlertTriangle size={15} /> Cần nâng cao ({matchResult.weak_skills.length})
                      </h4>
                      {matchResult.weak_skills.length === 0 ? (
                        <p className="text-muted text-xs">Không có kỹ năng yếu.</p>
                      ) : (
                        <ul className="skill-list-simple">
                          {matchResult.weak_skills.map((s) => (
                            <li key={s.skill_id}>
                              <span>{s.skill_name}</span>
                              <span className="badge badge-warning text-xs">{s.current_level} → {s.needed_level}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>

                    {/* Missing */}
                    <div className="skill-col">
                      <h4 className="skill-col-title text-danger">
                        <XCircle size={15} /> Còn thiếu ({matchResult.missing_skills.length})
                      </h4>
                      {matchResult.missing_skills.length === 0 ? (
                        <p className="text-muted text-xs">Bạn đã có đủ kỹ năng! 🎉</p>
                      ) : (
                        <ul className="skill-list-simple">
                          {matchResult.missing_skills.map((s) => (
                            <li key={s.skill_id}>
                              <span>{s.skill_name}</span>
                              {s.is_required && (
                                <span className="badge badge-danger text-xs">Bắt buộc</span>
                              )}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </div>

                  {/* AI Recommendation */}
                  {matchResult.ai_recommendation && (
                    <div className="ai-recommendation">
                      <h4>💡 Lời khuyên từ AI Career Advisor</h4>
                      <div className="ai-rec-content">
                        {matchResult.ai_recommendation.split('\n').filter(Boolean).map((line, i) => (
                          <p key={i}>{line}</p>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Job description (when no match result) */}
              {!matchResult && (
                <div className="job-description">
                  {selectedJob.description && (
                    <>
                      <h4>Mô tả công việc</h4>
                      <p className="text-secondary text-sm" style={{ marginTop: '0.5rem', lineHeight: 1.7 }}>
                        {selectedJob.description}
                      </p>
                    </>
                  )}

                  {selectedJob.job_skills.filter((s) => s.is_required).length > 0 && (
                    <>
                      <h4 style={{ marginTop: '1.5rem', marginBottom: '0.5rem' }}>
                        Kỹ năng bắt buộc
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {selectedJob.job_skills
                          .filter((s) => s.is_required)
                          .map((s) => (
                            <span key={s.skill_id} className="badge badge-primary">{s.skill_name}</span>
                          ))}
                      </div>
                    </>
                  )}

                  {selectedJob.job_skills.filter((s) => !s.is_required).length > 0 && (
                    <>
                      <h4 style={{ marginTop: '1.5rem', marginBottom: '0.5rem' }}>
                        Kỹ năng ưu tiên
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {selectedJob.job_skills
                          .filter((s) => !s.is_required)
                          .map((s) => (
                            <span key={s.skill_id} className="badge badge-neutral">{s.skill_name}</span>
                          ))}
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          ) : (
            /* No job selected */
            <div className="empty-job-state">
              <Briefcase size={52} className="text-muted" style={{ opacity: 0.4 }} />
              <h3>Chọn một vị trí</h3>
              <p className="text-muted text-sm">
                Chọn vị trí từ danh sách bên trái để xem chi tiết và so khớp với CV của bạn.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

