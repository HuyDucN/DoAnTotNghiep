import { useState, useEffect, useMemo } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { jobsApi, cvApi, getApiErrorMessage } from '../../services/api';
import type { Job, CV, SkillGapResult, PaginatedResponse } from '../../types';
import CvMatchStatusBadge from '../../components/CvMatchStatusBadge';
import QueryLoadNotice from '../../components/QueryLoadNotice';
import {
  Briefcase, MapPin, DollarSign, Search,
  Activity, Loader2, CheckCircle, XCircle,
  AlertTriangle, Filter, ChevronDown, ChevronLeft, ChevronRight,
} from 'lucide-react';
import toast from 'react-hot-toast';
import {
  PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart,
  ResponsiveContainer, Tooltip, Legend,
} from 'recharts';
import './JobsPage.css';
import { createMatchRequestTracker, getVisibleMatchResult, getRecordedMatchResult } from './matchRequest';
import type { MatchRequest, MatchOutcome } from './matchRequest';

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

const PAGE_SIZE = 10;
const EMPTY_JOBS: Job[] = [];
const MATCH_HISTORY_KEY = ['skill-gaps', 'mine'] as const;

function SkillGapRadar({ result }: { result: SkillGapResult }) {
  const groups = result.skill_group_scores;
  if (!groups || groups.every((group) => group.total_weight === 0)) return null;
  const data = groups.map((group) => ({
    importance: group.importance === 'high' ? 'Cao' : group.importance === 'medium' ? 'Trung bình' : 'Thấp',
    requirement: group.total_weight > 0 ? 100 : 0,
    candidate: group.score,
  }));

  return (
    <div className="skill-radar-card">
      <div className="skill-radar-heading">
        <h4>Biểu đồ Skill Gap</h4>
        <span className="text-muted text-xs">Theo mức độ quan trọng</span>
      </div>
      <div className="skill-radar-chart">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={data} outerRadius="68%">
            <PolarGrid stroke="rgba(148,163,184,0.25)" />
            <PolarAngleAxis dataKey="importance" tick={{ fill: '#cbd5e1', fontSize: 12 }} />
            <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 10 }} />
            <Radar name="Yêu cầu công việc" dataKey="requirement" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.12} />
            <Radar name="CV tại lần so khớp" dataKey="candidate" stroke="#818cf8" fill="#818cf8" fillOpacity={0.35} />
            <Tooltip formatter={(value) => `${value}%`} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      <p className="text-muted text-xs">
        Mỗi nhóm thể hiện tỷ lệ trọng số kỹ năng đã đáp ứng. Kỹ năng cần nâng cao chưa được cộng điểm.
      </p>
    </div>
  );
}

// Main component
export default function JobsPage() {
  const queryClient = useQueryClient();
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [selectedCvId, setSelectedCvId] = useState<number | ''>('');
  const [matchOutcome, setMatchOutcome] = useState<MatchOutcome | null>(null);
  const [pendingMatch, setPendingMatch] = useState<MatchRequest | null>(null);
  const [requestTracker] = useState(createMatchRequestTracker);
  const [search, setSearch] = useState('');
  const [filterLevel, setFilterLevel] = useState('');

  const jobParams = {
    page: currentPage,
    size: PAGE_SIZE,
    search: search.trim() || undefined,
    level: filterLevel || undefined,
  };
  const jobsQuery = useQuery<PaginatedResponse<Job>>({
    queryKey: ['jobs', jobParams],
    queryFn: () => jobsApi.list(jobParams),
  });

  const cvsQuery = useQuery<CV[]>({
    queryKey: ['cvs', 'mine'],
    queryFn: () => cvApi.list(),
  });

  const matchHistoryQuery = useQuery<SkillGapResult[]>({
    queryKey: MATCH_HISTORY_KEY,
    queryFn: () => jobsApi.getGapHistory(),
    enabled: matchOutcome !== null,
    staleTime: 0,
  });

  const jobsData = jobsQuery.data;
  const jobs = jobsData?.items ?? EMPTY_JOBS;
  const pagination = {
    total: jobsData?.total ?? 0,
    page: jobsData?.page ?? currentPage,
    size: jobsData?.size ?? PAGE_SIZE,
    pages: jobsData?.pages ?? 1,
  };
  const cvs = useMemo(
    () => (cvsQuery.data ?? []).filter((cv) => cv.status === 'analyzed'),
    [cvsQuery.data],
  );
  const loadingJobs = jobsQuery.isPending || cvsQuery.isPending;

  const activeCv = cvs.find((cv) => cv.id === selectedCvId) ?? cvs[0];
  const activeCvId = activeCv?.id ?? '';
  const hasSelectedMatch = getVisibleMatchResult(matchOutcome, selectedJob?.id, activeCvId) !== null;
  const matchResult = getRecordedMatchResult(matchOutcome, selectedJob?.id, activeCvId, matchHistoryQuery.data);
  const matching = pendingMatch !== null && pendingMatch.jobId === selectedJob?.id && pendingMatch.cvId === activeCvId;

  const clearMatch = () => {
    requestTracker.invalidate();
    setMatchOutcome(null);
    setPendingMatch(null);
  };
  const selectJob = (job: Job) => {
    clearMatch();
    setSelectedJob(job);
  };
  const selectCv = (cvId: number) => {
    clearMatch();
    setSelectedCvId(cvId);
  };

  useEffect(() => () => requestTracker.invalidate(), [requestTracker]);

  const matchMutation = useMutation<SkillGapResult, unknown, MatchRequest>({
    mutationFn: ({ jobId, cvId }) =>
      jobsApi.match(jobId, cvId),
    onSuccess: (result, request) => {
      // Yêu cầu cũ vẫn có thể đã lưu kết quả trên server, nên làm mới lịch sử.
      if (!requestTracker.complete(request)) {
        void queryClient.invalidateQueries({ queryKey: MATCH_HISTORY_KEY, exact: true });
        return;
      }
      setPendingMatch(null);
      const outcome = { request, result };
      if (!getVisibleMatchResult(outcome, request.jobId, request.cvId)) {
        setMatchOutcome(null);
        void queryClient.invalidateQueries({ queryKey: MATCH_HISTORY_KEY, exact: true });
        toast.error('Kết quả so khớp không đúng CV hoặc công việc đã chọn. Vui lòng thử lại.');
        return;
      }
      // Bỏ bản đọc trước khi so khớp; chỉ hiển thị bản server trả sau lần lưu này.
      void queryClient.resetQueries({ queryKey: MATCH_HISTORY_KEY, exact: true });
      setMatchOutcome(outcome);
      toast.success('So khớp thành công!');
    },
    onError: (error, request) => {
      if (!requestTracker.complete(request)) return;
      setPendingMatch(null);
      toast.error(getApiErrorMessage(error, 'Lỗi khi so khớp. Thử lại.'));
    },
  });

  const handleMatch = () => {
    if (matching) return;
    if (!selectedJob) return toast.error('Vui lòng chọn một công việc.');
    if (!activeCvId) return toast.error('Vui lòng chọn CV đã phân tích.');

    const request = requestTracker.begin(selectedJob.id, Number(activeCvId));
    setMatchOutcome(null);
    setPendingMatch(request);
    matchMutation.mutate(request);
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
              onChange={(e) => { setSearch(e.target.value); setCurrentPage(1); }}
            />
          </div>

          {/* Level filter */}
          <div className="filter-bar mb-4">
            <Filter size={14} className="text-muted" />
            <select
              className="filter-select"
              value={filterLevel}
              onChange={(e) => { setFilterLevel(e.target.value); setCurrentPage(1); }}
            >
              <option value="">Tất cả cấp độ</option>
              {Object.entries(LEVEL_LABELS).map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </select>
            <ChevronDown size={13} className="text-muted" />
          </div>

          <QueryLoadNotice query={jobsQuery} label="danh sách công việc" />
          <QueryLoadNotice query={cvsQuery} label="danh sách CV" />

          {/* Jobs count */}
          <p className="jobs-count text-muted text-xs mb-4">
            {loadingJobs ? '...' : jobsQuery.data !== undefined ? `${pagination.total} vị trí · Trang ${pagination.page}/${pagination.pages}` : '—'}
          </p>

          {loadingJobs ? (
            <div className="flex justify-center p-8">
              <Loader2 className="animate-spin text-brand" size={24} />
            </div>
          ) : !jobsQuery.isSuccess ? null : jobs.length === 0 ? (
            <div className="empty-state" style={{ minHeight: '200px' }}>
              <Briefcase size={36} className="text-muted" />
              <p className="text-muted text-sm">
                {search.trim() || filterLevel ? 'Không tìm thấy vị trí phù hợp.' : 'Chưa có vị trí nào được đăng.'}
              </p>
            </div>
          ) : (
            <div className="job-cards">
              {jobs.map((job) => (
                <div
                  key={job.id}
                  className={`job-card${selectedJob?.id === job.id ? ' selected' : ''}`}
                  onClick={() => selectJob(job)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      selectJob(job);
                    }
                  }}
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

          {/* Pagination Controls */}
          {!loadingJobs && pagination.pages > 1 && (
            <div className="pagination-controls">
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage <= 1 || jobsQuery.isFetching}
                aria-label="Trang trước"
              >
                <ChevronLeft size={16} /> Trước
              </button>
              <span className="pagination-info text-muted text-xs">
                {currentPage} / {pagination.pages}
              </span>
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => setCurrentPage((p) => Math.min(pagination.pages, p + 1))}
                disabled={currentPage >= pagination.pages || jobsQuery.isFetching}
                aria-label="Trang sau"
              >
                Sau <ChevronRight size={16} />
              </button>
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
                  Chọn CV đã phân tích để so sánh kỹ năng với yêu cầu vị trí này:
                </p>
                <div className="match-controls">
                  <div className="form-group flex-1" style={{ marginBottom: 0 }}>
                    <label className="form-label">CV của bạn</label>
                    {!cvsQuery.isSuccess ? (
                      <p className="text-warning text-sm">
                        Chưa tải được danh sách CV. Hãy thử lại ở thông báo phía trên.
                      </p>
                    ) : cvs.length === 0 ? (
                      <p className="text-warning text-sm">
                        ⚠ Bạn chưa có CV nào được phân tích. Hãy tải CV lên ở trang <strong>CV của tôi</strong>.
                      </p>
                    ) : (
                      <select
                        className="form-input"
                        value={activeCvId}
                        onChange={(e) => selectCv(Number(e.target.value))}
                      >
                        {cvs.map((cv) => (
                          <option key={cv.id} value={cv.id}>{cv.filename} (CV #{cv.id})</option>
                        ))}
                      </select>
                    )}
                  </div>
                  <button
                    className="btn btn-primary match-btn"
                    onClick={handleMatch}
                    disabled={matching || !activeCvId || cvs.length === 0}
                  >
                    {matching
                      ? <><Loader2 className="animate-spin" size={16} /> Đang phân tích...</>
                      : <><Activity size={16} /> Phân tích độ phù hợp</>
                    }
                  </button>
                </div>
              </div>

              {/* Match result */}
              {hasSelectedMatch && !matchResult && (matchHistoryQuery.isPending || matchHistoryQuery.isFetching) && (
                <div className="match-result-area flex items-center gap-2" role="status">
                  <Loader2 className="animate-spin" size={18} /> Đang tải kết quả đã lưu...
                </div>
              )}
              {hasSelectedMatch && matchHistoryQuery.isError && (
                <div className="match-result-area" role="alert">
                  <p className="text-warning text-sm">
                    Đã lưu kết quả so khớp nhưng chưa tải được dữ liệu mới nhất.{' '}
                    {getApiErrorMessage(matchHistoryQuery.error, 'Vui lòng thử tải lại.')}
                  </p>
                  <button className="btn btn-outline btn-sm mt-3" onClick={() => void matchHistoryQuery.refetch()}>
                    Thử tải lại kết quả
                  </button>
                </div>
              )}
              {hasSelectedMatch && matchHistoryQuery.isSuccess && !matchHistoryQuery.isFetching && !matchResult && (
                <p className="match-result-area text-warning text-sm" role="status">
                  Kết quả đã lưu không còn trong danh sách hiện tại. Vui lòng tải lại danh sách CV và so khớp lại.
                </p>
              )}
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
                    <div className="match-score-details">
                      <h3>Kết quả phân tích</h3>
                      <p className="text-muted text-sm" style={{ marginTop: '0.25rem' }}>
                        Kết quả của <strong>CV #{matchResult.cv_id} · {matchResult.cv_filename}</strong> cho vị trí <strong>{matchResult.job.title}</strong>.
                      </p>
                      <CvMatchStatusBadge status={matchResult.cv_match_status} detailed />
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

                  <SkillGapRadar result={matchResult} />
                  {matchResult.skill_group_scores?.every((group) => group.total_weight === 0) && (
                    <p className="text-muted text-sm">Công việc chưa khai báo kỹ năng để tính điểm phù hợp.</p>
                  )}

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

