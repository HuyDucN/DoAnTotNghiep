import { useState, useEffect } from 'react';
import { useAuthStore } from '../../store/authStore';
import { usersApi, cvApi } from '../../services/api';
import type { Profile, CV, CVAnalysis } from '../../types';
import {
  MapPin, Briefcase, Mail, Phone, Award, Code,
  BookOpen, FileText, CheckCircle, XCircle, Loader2,
  Clock, ChevronRight, Sparkles, FolderOpen, ChevronDown,
} from 'lucide-react';
import toast from 'react-hot-toast';
import './SkillProfile.css';

const STATUS_ICON: Record<string, React.ReactNode> = {
  analyzed: <CheckCircle size={14} />,
  failed: <XCircle size={14} />,
  processing: <Loader2 size={14} className="animate-spin" />,
  uploaded: <Clock size={14} />,
};

const STATUS_LABEL: Record<string, string> = {
  analyzed: 'Đã phân tích',
  failed: 'Thất bại',
  processing: 'Đang xử lý',
  uploaded: 'Đã tải lên',
};

const CAT_LABELS: Record<string, string> = {
  programming_language: '💻 Ngôn ngữ',
  framework: '⚙️ Framework',
  database: '🗄️ Database',
  cloud: '☁️ Cloud',
  devops: '🚀 DevOps',
  ai_ml: '🧠 AI / ML',
  soft_skill: '🧩 Kỹ năng mềm',
  tool: '🛠️ Công cụ',
  other: '📦 Khác',
};
const CAT_ORDER = ['programming_language', 'framework', 'database', 'cloud', 'devops', 'ai_ml', 'soft_skill', 'tool', 'other'];

export default function SkillProfilePage() {
  const user = useAuthStore((s) => s.user);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [analyzedCvs, setAnalyzedCvs] = useState<CV[]>([]);
  const [selectedCvId, setSelectedCvId] = useState<number | null>(null);
  const [cvHistory, setCvHistory] = useState<CV[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [profileData, cvsData] = await Promise.all([
          usersApi.getProfile(),
          cvApi.list(),
        ]);
        setProfile(profileData);
        setCvHistory(cvsData);
        const analyzed: CV[] = cvsData.filter((cv: CV) => cv.status === 'analyzed' && cv.ai_analysis);
        setAnalyzedCvs(analyzed);
        if (analyzed.length > 0) setSelectedCvId(analyzed[0].id);
      } catch {
        toast.error('Lỗi tải dữ liệu profile');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="profile-loading">
        <Loader2 size={28} className="animate-spin text-brand" />
        <p className="text-muted text-sm mt-3">Đang tải hồ sơ...</p>
      </div>
    );
  }

  const activeCv = analyzedCvs.find((c) => c.id === selectedCvId) ?? analyzedCvs[0] ?? null;
  const analysis: CVAnalysis | undefined = activeCv?.ai_analysis;

  const displayName = analysis?.full_name?.trim() || user?.full_name || 'Người dùng';
  const displaySummary = analysis?.summary?.trim() || profile?.job_title || '';
  const displayPhone = analysis?.phone?.trim() || profile?.phone || '';
  const displayLocation = analysis?.location?.trim() || profile?.location || '';
  const initials = displayName.split(' ').map((w) => w[0]).slice(-2).join('').toUpperCase();

  const hasAnalysis = !!analysis;
  const skillCount = analysis?.skills?.length ?? 0;
  const expYears = analysis?.total_experience_years ?? 0;

  return (
    <div className="skill-profile-page animate-fade-in">
      <div className="profile-hero card">
        <div className="profile-hero-bg" aria-hidden />
        <div className="profile-hero-body">
          <div className="profile-avatar-wrap">
            <div className="profile-avatar bg-brand">{initials}</div>
            {hasAnalysis && (
              <span className="avatar-badge" title="Đã phân tích bằng AI">
                <Sparkles size={11} />
              </span>
            )}
          </div>

          <div className="profile-identity">
            <h2 className="profile-name">{displayName}</h2>
            {displaySummary && (
              <p className="profile-headline">{displaySummary}</p>
            )}
            <div className="profile-contact-row">
              <span><Mail size={13} />{user?.email}</span>
              {displayPhone && <span><Phone size={13} />{displayPhone}</span>}
              {displayLocation && <span><MapPin size={13} />{displayLocation}</span>}
            </div>
          </div>

          <div className="profile-right-group">
            {analyzedCvs.length > 1 && (
              <div className="cv-selector">
                <label className="cv-selector-label">CV hiển thị</label>
                <div className="cv-selector-wrap">
                  <FileText size={13} className="text-muted" />
                  <select
                    className="cv-selector-select"
                    value={selectedCvId ?? ''}
                    onChange={(e) => setSelectedCvId(Number(e.target.value))}
                  >
                    {analyzedCvs.map((cv) => (
                      <option key={cv.id} value={cv.id}>{cv.filename}</option>
                    ))}
                  </select>
                  <ChevronDown size={12} className="text-muted" />
                </div>
              </div>
            )}
            <div className="profile-stat-group">
              <div className="profile-stat">
                <strong>{expYears}</strong>
                <span>Năm KN</span>
              </div>
              <div className="profile-stat">
                <strong>{skillCount}</strong>
                <span>Kỹ năng</span>
              </div>
              <div className="profile-stat">
                <strong>{cvHistory.filter((c) => c.status === 'analyzed').length}</strong>
                <span>CV đã PT</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="profile-body-grid">
        <aside className="profile-sidebar">
          <div className="card sidebar-card">
            <div className="sidebar-card-header">
              <FileText size={15} />
              <span>Hồ sơ CV</span>
              <span className="sidebar-badge">{cvHistory.length}</span>
            </div>
            {cvHistory.length === 0 ? (
              <p className="text-muted text-xs sidebar-empty">Chưa có CV nào.</p>
            ) : (
              <div className="cv-compact-list">
                {cvHistory.map((cv) => (
                  <div
                    key={cv.id}
                    className={`cv-compact-item${cv.id === (activeCv?.id) ? ' active' : ''}${cv.status === 'analyzed' ? ' clickable' : ''}`}
                    onClick={() => cv.status === 'analyzed' && cv.ai_analysis && setSelectedCvId(cv.id)}
                    title={cv.status === 'analyzed' ? 'Nhấn để xem CV này' : STATUS_LABEL[cv.status]}
                  >
                    <div className={`cv-status-dot status-${cv.status}`} />
                    <div className="cv-compact-info">
                      <span className="cv-compact-name" title={cv.filename}>{cv.filename}</span>
                      <span className="cv-compact-meta">
                        {new Date(cv.created_at).toLocaleDateString('vi-VN')}
                        <span className={`cv-status-tag status-${cv.status}`}>
                          {STATUS_ICON[cv.status]} {STATUS_LABEL[cv.status] || cv.status}
                        </span>
                      </span>
                    </div>
                    {cv.id === activeCv?.id && <ChevronRight size={14} className="text-brand" />}
                  </div>
                ))}
              </div>
            )}
          </div>

          {analysis?.education && analysis.education.length > 0 && (
            <div className="card sidebar-card mt-4">
              <div className="sidebar-card-header">
                <BookOpen size={15} />
                <span>Học vấn</span>
              </div>
              <div className="edu-mini-list">
                {analysis.education.map((edu, i) => (
                  <div key={i} className="edu-mini-item">
                    <strong>{edu.degree} — {edu.field_of_study}</strong>
                    <span>{edu.institution}</span>
                    {(edu.start_year || edu.end_year) && (
                      <span className="text-muted">{edu.start_year} – {edu.end_year ?? 'Nay'}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {analysis?.certificates && analysis.certificates.length > 0 && (
            <div className="card sidebar-card mt-4">
              <div className="sidebar-card-header">
                <Award size={15} />
                <span>Chứng chỉ</span>
              </div>
              <div className="cert-mini-list">
                {analysis.certificates.map((cert, i) => (
                  <div key={i} className="cert-mini-item">
                    <Award size={13} className="text-warning" />
                    <div>
                      <strong>{cert.name}</strong>
                      {cert.issuer && <span>{cert.issuer}{cert.year ? ` · ${cert.year}` : ''}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </aside>

        <main className="profile-main">
          {!hasAnalysis ? (
            <div className="card no-analysis-state">
              <Sparkles size={36} className="text-brand mb-3" />
              <h3>Chưa có dữ liệu phân tích</h3>
              <p className="text-muted text-sm">
                Tải lên CV và để AI phân tích để hiển thị kỹ năng, kinh nghiệm của bạn tại đây.
              </p>
            </div>
          ) : (
            <>
              <div className="card">
                <div className="panel-header">
                  <div className="flex items-center gap-2">
                    <Code size={17} className="text-brand" />
                    <h3>Kỹ năng</h3>
                    {skillCount > 0 && <span className="count-chip">{skillCount}</span>}
                  </div>
                </div>
                {skillCount === 0 ? (
                  <p className="text-muted text-sm">Chưa phát hiện kỹ năng nào từ CV.</p>
                ) : (
                  <div className="skills-grid">
                    {CAT_ORDER.map((cat) => {
                      const skills = analysis!.skills.filter((s) => s.category === cat);
                      if (!skills.length) return null;
                      return (
                        <div key={cat} className="skill-cat-block">
                          <h4 className="skill-cat-label">{CAT_LABELS[cat]}</h4>
                          <div className="skill-pill-row">
                            {skills.map((skill) => (
                              <span key={skill.name} className={`skill-pill-item level-${skill.proficiency_level}`}>
                                {skill.name}
                                <em>{skill.proficiency_level}</em>
                              </span>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {analysis!.experience && analysis!.experience.length > 0 && (
                <div className="card mt-4">
                  <div className="panel-header">
                    <div className="flex items-center gap-2">
                      <Briefcase size={17} className="text-brand" />
                      <h3>Kinh nghiệm làm việc</h3>
                    </div>
                  </div>
                  <div className="timeline">
                    {analysis!.experience.map((exp, i) => (
                      <div key={i} className="timeline-item">
                        <div className="timeline-dot" />
                        <div className="timeline-content">
                          <h4>{exp.position} <span className="timeline-company">@ {exp.company}</span></h4>
                          <div className="timeline-date">
                            {exp.start_date}{exp.end_date ? ` — ${exp.end_date}` : ' — Hiện tại'}
                          </div>
                          {exp.description && (
                            <p className="timeline-desc">{exp.description}</p>
                          )}
                          {exp.skills_used?.length > 0 && (
                            <div className="timeline-tags">
                              {exp.skills_used.map((s) => (
                                <span key={s} className="mini-skill">{s}</span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {analysis!.projects && analysis!.projects.length > 0 && (
                <div className="card mt-4">
                  <div className="panel-header">
                    <div className="flex items-center gap-2">
                      <FolderOpen size={17} className="text-brand" />
                      <h3>Dự án</h3>
                      <span className="count-chip">{analysis!.projects.length}</span>
                    </div>
                  </div>
                  <div className="projects-grid">
                    {analysis!.projects.map((proj, i) => (
                      <div key={i} className="project-card">
                        <h4 className="project-title">{proj.name}</h4>
                        {proj.description && (
                          <p className="project-desc">{proj.description}</p>
                        )}
                        {proj.technologies?.length > 0 && (
                          <div className="project-tech">
                            {proj.technologies.map((t) => (
                              <span key={t} className="mini-skill">{t}</span>
                            ))}
                          </div>
                        )}
                        {proj.url && (
                          <a href={proj.url} target="_blank" rel="noopener noreferrer" className="project-link">
                            🔗 Xem dự án
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}



