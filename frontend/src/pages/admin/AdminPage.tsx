import { useState, useEffect, useCallback } from 'react';
import { isAxiosError } from 'axios';
import { jobsApi, skillsApi, adminApi } from '../../services/api';
import type { Job, Skill, CV, User, JobSkillInput } from '../../types';
import { useAuthStore } from '../../store/authStore';
import {
  Briefcase, Wrench, Plus, Pencil, Trash2, X, Search,
  Loader2, AlertTriangle, ShieldCheck, BookOpen, Database,
  Save, RefreshCw, FileText, Users, UserCheck, UserX,
} from 'lucide-react';
import toast from 'react-hot-toast';
import './AdminPage.css';

// ──────────────────────────────────────────────────────────────────────────────
// Constants
// ──────────────────────────────────────────────────────────────────────────────
const JOB_TYPES  = ['full_time', 'part_time', 'contract', 'internship', 'remote'];
const JOB_LEVELS = ['intern', 'junior', 'mid', 'senior', 'lead'];
const JOB_CATS   = [
  'backend', 'frontend', 'fullstack', 'mobile', 'devops',
  'data_science', 'ai_ml', 'design', 'qa', 'product', 'other',
];
const SKILL_CATS = [
  'programming_language', 'framework', 'database',
  'cloud', 'devops', 'ai_ml', 'soft_skill', 'tool', 'other',
];
const IMPORTANCE_OPTS: Array<'high' | 'medium' | 'low'> = ['high', 'medium', 'low'];

// ──────────────────────────────────────────────────────────────────────────────
// Sub-types
// ──────────────────────────────────────────────────────────────────────────────
type AdminTab = 'jobs' | 'skills' | 'cvs' | 'users';

interface JobFormData {
  title: string;
  company: string;
  location: string;
  job_type: string;
  level: string;
  category: string;
  description: string;
  salary_min: string;
  salary_max: string;
  required_skills: JobSkillInput[];
  preferred_skills: JobSkillInput[];
}

interface SkillFormData {
  name: string;
  category: string;
  description: string;
}

const defaultJobForm = (): JobFormData => ({
  title: '', company: '', location: '',
  job_type: 'full_time', level: 'junior', category: 'backend',
  description: '', salary_min: '', salary_max: '',
  required_skills: [], preferred_skills: [],
});

const defaultSkillForm = (): SkillFormData => ({
  name: '', category: 'other', description: '',
});

// ──────────────────────────────────────────────────────────────────────────────
// Helper components
// ──────────────────────────────────────────────────────────────────────────────

function CatBadge({ cat }: { cat: string }) {
  return (
    <span className={`cat-badge cat-${cat}`}>
      {cat.replace(/_/g, ' ')}
    </span>
  );
}

function LevelBadge({ level }: { level: string }) {
  return <span className={`level-badge level-${level}`}>{level}</span>;
}

// ──────────────────────────────────────────────────────────────────────────────
// Confirm Delete Modal
// ──────────────────────────────────────────────────────────────────────────────
interface ConfirmModalProps {
  label: string;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
}

function ConfirmModal({ label, onConfirm, onCancel, loading }: ConfirmModalProps) {
  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-panel modal-sm" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Xác nhận xóa</h3>
          <button className="modal-close" onClick={onCancel}><X size={16} /></button>
        </div>
        <div className="modal-body">
          <div className="confirm-body">
            <div className="confirm-icon"><AlertTriangle size={28} /></div>
            <h4>Bạn có chắc chắn muốn xóa?</h4>
            <p className="mt-2">
              <strong style={{ color: 'var(--text-primary)' }}>{label}</strong> sẽ bị xóa
              vĩnh viễn và không thể khôi phục.
            </p>
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={onCancel} disabled={loading}>Hủy</button>
          <button className="btn btn-danger" onClick={onConfirm} disabled={loading}>
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={16} />}
            Xóa
          </button>
        </div>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Skill Row Builder (inside Job modal)
// ──────────────────────────────────────────────────────────────────────────────
interface SkillBuilderProps {
  label: string;
  type: 'required' | 'preferred';
  skills: JobSkillInput[];
  onChange: (updated: JobSkillInput[]) => void;
}

function SkillBuilder({ label, type, skills, onChange }: SkillBuilderProps) {
  const [newName, setNewName]         = useState('');
  const [newImportance, setNewImportance] = useState<'high' | 'medium' | 'low'>('medium');

  const add = () => {
    const trimmed = newName.trim();
    if (!trimmed) return;
    onChange([...skills, { skill_name: trimmed, is_required: type === 'required', importance: newImportance }]);
    setNewName('');
    setNewImportance('medium');
  };

  const remove = (idx: number) => onChange(skills.filter((_, i) => i !== idx));

  return (
    <div className="skills-section">
      <p className="skills-section-title">
        {type === 'required' ? '🔴' : '🟡'} {label}
      </p>
      <div className="skill-badge-group">
        {skills.length === 0 && <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem', alignSelf: 'center' }}>Chưa có skill</span>}
        {skills.map((s, i) => (
          <span key={i} className={`skill-badge-item ${type}`}>
            {s.skill_name}
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginLeft: 4 }}>({s.importance})</span>
            <button className="skill-badge-remove" onClick={() => remove(i)} type="button">
              <X size={12} />
            </button>
          </span>
        ))}
      </div>
      <div className="skill-add-row">
        <div className="form-group">
          <input
            type="text"
            className="form-input"
            placeholder="Tên skill (vd: Python, React...)"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), add())}
          />
        </div>
        <div className="form-group">
          <select className="form-input" value={newImportance} onChange={(e) => setNewImportance(e.target.value as any)}>
            {IMPORTANCE_OPTS.map(o => <option key={o} value={o}>{o}</option>)}
          </select>
        </div>
        <button type="button" className="btn btn-secondary" style={{ marginBottom: '20px' }} onClick={add}>
          <Plus size={16} />
        </button>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Job Modal
// ──────────────────────────────────────────────────────────────────────────────
interface JobModalProps {
  job: Job | null; // null = create mode
  onClose: () => void;
  onSaved: () => void;
}

function JobModal({ job, onClose, onSaved }: JobModalProps) {
  const isEdit = !!job;
  const [form, setForm] = useState<JobFormData>(() => {
    if (job) {
      return {
        title: job.title,
        company: job.company || '',
        location: job.location || '',
        job_type: job.job_type,
        level: job.level,
        category: job.category,
        description: job.description || '',
        salary_min: job.salary_min?.toString() || '',
        salary_max: job.salary_max?.toString() || '',
        required_skills:  job.job_skills
          .filter(s => s.is_required)
          .map(s => ({ skill_name: s.skill_name, is_required: true, importance: s.importance as any })),
        preferred_skills: job.job_skills
          .filter(s => !s.is_required)
          .map(s => ({ skill_name: s.skill_name, is_required: false, importance: s.importance as any })),
      };
    }
    return defaultJobForm();
  });
  const [saving, setSaving] = useState(false);

  const set = (key: keyof JobFormData, val: any) => setForm(f => ({ ...f, [key]: val }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title.trim()) return toast.error('Tiêu đề job không được để trống');

    const payload = {
      title: form.title.trim(),
      company: form.company || null,
      location: form.location || null,
      job_type: form.job_type,
      level: form.level,
      category: form.category,
      description: form.description || null,
      salary_min: form.salary_min ? Number(form.salary_min) : null,
      salary_max: form.salary_max ? Number(form.salary_max) : null,
      required_skills:  form.required_skills,
      preferred_skills: form.preferred_skills,
    };

    setSaving(true);
    try {
      if (isEdit) {
        await jobsApi.update(job!.id, payload);
        toast.success('Cập nhật job thành công!');
      } else {
        await jobsApi.create(payload);
        toast.success('Tạo job thành công!');
      }
      onSaved();
      onClose();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Có lỗi xảy ra');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-panel" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{isEdit ? '✏️ Sửa Job' : '➕ Tạo Job mới'}</h3>
          <button className="modal-close" onClick={onClose}><X size={16} /></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="form-grid">
              {/* Title - span 2 */}
              <div className="form-group form-span-2">
                <label className="form-label">Tiêu đề <span style={{ color: 'var(--color-danger)' }}>*</span></label>
                <input className="form-input" value={form.title} onChange={e => set('title', e.target.value)} placeholder="Vd: Senior Backend Developer" required />
              </div>

              <div className="form-group">
                <label className="form-label">Công ty</label>
                <input className="form-input" value={form.company} onChange={e => set('company', e.target.value)} placeholder="Tên công ty" />
              </div>

              <div className="form-group">
                <label className="form-label">Địa điểm</label>
                <input className="form-input" value={form.location} onChange={e => set('location', e.target.value)} placeholder="Vd: Hà Nội, Remote..." />
              </div>

              <div className="form-group">
                <label className="form-label">Loại hình</label>
                <select className="form-input" value={form.job_type} onChange={e => set('job_type', e.target.value)}>
                  {JOB_TYPES.map(t => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Cấp độ</label>
                <select className="form-input" value={form.level} onChange={e => set('level', e.target.value)}>
                  {JOB_LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
                </select>
              </div>

              <div className="form-group form-span-2">
                <label className="form-label">Danh mục</label>
                <select className="form-input" value={form.category} onChange={e => set('category', e.target.value)}>
                  {JOB_CATS.map(c => <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>)}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Lương từ (USD)</label>
                <input className="form-input" type="number" min={0} value={form.salary_min} onChange={e => set('salary_min', e.target.value)} placeholder="0" />
              </div>

              <div className="form-group">
                <label className="form-label">Lương đến (USD)</label>
                <input className="form-input" type="number" min={0} value={form.salary_max} onChange={e => set('salary_max', e.target.value)} placeholder="0" />
              </div>

              <div className="form-group form-span-2">
                <label className="form-label">Mô tả công việc</label>
                <textarea
                  className="form-input"
                  rows={4}
                  value={form.description}
                  onChange={e => set('description', e.target.value)}
                  placeholder="Mô tả chi tiết về vị trí, trách nhiệm..."
                  style={{ resize: 'vertical' }}
                />
              </div>

              {/* Skills Builders */}
              <SkillBuilder
                label="Kỹ năng bắt buộc (Required)"
                type="required"
                skills={form.required_skills}
                onChange={(v) => set('required_skills', v)}
              />
              <SkillBuilder
                label="Kỹ năng ưu tiên (Preferred)"
                type="preferred"
                skills={form.preferred_skills}
                onChange={(v) => set('preferred_skills', v)}
              />
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-ghost" onClick={onClose} disabled={saving}>Hủy</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
              {isEdit ? 'Cập nhật' : 'Tạo Job'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Skill Modal
// ──────────────────────────────────────────────────────────────────────────────
interface SkillModalProps {
  skill: Skill | null;
  onClose: () => void;
  onSaved: () => void;
}

function SkillModal({ skill, onClose, onSaved }: SkillModalProps) {
  const isEdit = !!skill;
  const [form, setForm] = useState<SkillFormData>(() =>
    isEdit
      ? { name: skill!.name, category: skill!.category, description: skill!.description || '' }
      : defaultSkillForm()
  );
  const [saving, setSaving] = useState(false);

  const set = (key: keyof SkillFormData, val: string) => setForm(f => ({ ...f, [key]: val }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return toast.error('Tên skill không được để trống');

    const payload = {
      name: form.name.trim(),
      category: form.category,
      description: form.description || undefined,
    };

    setSaving(true);
    try {
      if (isEdit) {
        await skillsApi.update(skill!.id, payload);
        toast.success('Cập nhật skill thành công!');
      } else {
        await skillsApi.create(payload);
        toast.success('Thêm skill thành công!');
      }
      onSaved();
      onClose();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Có lỗi xảy ra');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-panel modal-sm" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{isEdit ? '✏️ Sửa Skill' : '➕ Thêm Skill'}</h3>
          <button className="modal-close" onClick={onClose}><X size={16} /></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="form-grid one-col">
              <div className="form-group">
                <label className="form-label">Tên kỹ năng <span style={{ color: 'var(--color-danger)' }}>*</span></label>
                <input className="form-input" value={form.name} onChange={e => set('name', e.target.value)} placeholder="Vd: Python, React, Docker..." required />
              </div>
              <div className="form-group">
                <label className="form-label">Danh mục</label>
                <select className="form-input" value={form.category} onChange={e => set('category', e.target.value)}>
                  {SKILL_CATS.map(c => <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Mô tả (tùy chọn)</label>
                <textarea
                  className="form-input"
                  rows={3}
                  value={form.description}
                  onChange={e => set('description', e.target.value)}
                  placeholder="Mô tả ngắn về kỹ năng..."
                  style={{ resize: 'vertical' }}
                />
              </div>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-ghost" onClick={onClose} disabled={saving}>Hủy</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
              {isEdit ? 'Cập nhật' : 'Thêm Skill'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Jobs Tab
// ──────────────────────────────────────────────────────────────────────────────
function JobsTab() {
  const [jobs, setJobs]         = useState<Job[]>([]);
  const [loading, setLoading]   = useState(true);
  const [search, setSearch]     = useState('');
  const [catFilter, setCatFilter] = useState('');

  const [modalJob, setModalJob] = useState<Job | null | undefined>(undefined); // undefined = closed, null = create
  const [deleteTarget, setDeleteTarget] = useState<Job | null>(null);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await jobsApi.list();
      setJobs(data);
    } catch {
      toast.error('Lỗi tải danh sách jobs');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await jobsApi.delete(deleteTarget.id);
      toast.success('Đã xóa job');
      setDeleteTarget(null);
      load();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Lỗi khi xóa');
    } finally {
      setDeleting(false);
    }
  };

  const filtered = jobs.filter(j => {
    const q = search.toLowerCase();
    const matchSearch = !search || j.title.toLowerCase().includes(q) || (j.company || '').toLowerCase().includes(q);
    const matchCat    = !catFilter || j.category === catFilter;
    return matchSearch && matchCat;
  });

  return (
    <>
      {/* Stats */}
      <div className="admin-stats">
        <div className="admin-stat-card">
          <div className="admin-stat-icon"><Briefcase size={20} /></div>
          <div><p>Tổng số Jobs</p><strong>{jobs.length}</strong></div>
        </div>
        <div className="admin-stat-card">
          <div className="admin-stat-icon" style={{ background: 'rgba(16,185,129,0.15)', color: 'var(--color-success)' }}>
            <ShieldCheck size={20} />
          </div>
          <div><p>Đang hoạt động</p><strong>{jobs.filter(j => j.is_active).length}</strong></div>
        </div>
        <div className="admin-stat-card">
          <div className="admin-stat-icon" style={{ background: 'rgba(245,158,11,0.15)', color: 'var(--color-warning)' }}>
            <BookOpen size={20} />
          </div>
          <div><p>Danh mục</p><strong>{new Set(jobs.map(j => j.category)).size}</strong></div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="admin-toolbar">
        <div className="admin-search">
          <Search size={16} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
          <input
            placeholder="Tìm theo tiêu đề, công ty..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <select className="filter-select" value={catFilter} onChange={e => setCatFilter(e.target.value)}>
          <option value="">Tất cả danh mục</option>
          {JOB_CATS.map(c => <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>)}
        </select>
        <button className="btn btn-ghost" onClick={load} title="Làm mới">
          <RefreshCw size={16} />
        </button>
        <button className="btn btn-primary" onClick={() => setModalJob(null)}>
          <Plus size={16} /> Tạo Job
        </button>
      </div>

      {/* Table */}
      <div className="admin-table-wrap">
        {loading ? (
          <div className="admin-empty">
            <Loader2 size={36} className="animate-spin" style={{ color: 'var(--brand-primary)' }} />
            <p style={{ marginTop: 16 }}>Đang tải...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="admin-empty">
            <Briefcase size={48} />
            <h3>Chưa có job nào</h3>
            <p>Nhấn "+ Tạo Job" để bắt đầu</p>
          </div>
        ) : (
          <table className="admin-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Tiêu đề</th>
                <th>Công ty</th>
                <th>Cấp độ</th>
                <th>Danh mục</th>
                <th>Skills</th>
                <th>Ngày tạo</th>
                <th>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(job => (
                <tr key={job.id}>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>#{job.id}</td>
                  <td>
                    <div style={{ fontWeight: 600 }}>{job.title}</div>
                    {!job.is_active && (
                      <span style={{ fontSize: '0.7rem', color: 'var(--color-warning)' }}>● Ẩn</span>
                    )}
                  </td>
                  <td style={{ color: 'var(--text-secondary)' }}>{job.company || '—'}</td>
                  <td><LevelBadge level={job.level} /></td>
                  <td><CatBadge cat={job.category} /></td>
                  <td>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      {job.job_skills.filter(s => s.is_required).length} req /&nbsp;
                      {job.job_skills.filter(s => !s.is_required).length} pref
                    </span>
                  </td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                    {new Date(job.created_at).toLocaleDateString('vi-VN')}
                  </td>
                  <td>
                    <div className="admin-table-actions">
                      <button className="icon-btn" onClick={() => setModalJob(job)} title="Sửa">
                        <Pencil size={14} />
                      </button>
                      <button className="icon-btn danger" onClick={() => setDeleteTarget(job)} title="Xóa">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Modals */}
      {modalJob !== undefined && (
        <JobModal
          job={modalJob}
          onClose={() => setModalJob(undefined)}
          onSaved={load}
        />
      )}
      {deleteTarget && (
        <ConfirmModal
          label={deleteTarget.title}
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
          loading={deleting}
        />
      )}
    </>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Skills Tab
// ──────────────────────────────────────────────────────────────────────────────
function SkillsTab() {
  const [skills, setSkills]     = useState<Skill[]>([]);
  const [loading, setLoading]   = useState(true);
  const [search, setSearch]     = useState('');
  const [catFilter, setCatFilter] = useState('');

  const [modalSkill, setModalSkill] = useState<Skill | null | undefined>(undefined);
  const [deleteTarget, setDeleteTarget] = useState<Skill | null>(null);
  const [deleting, setDeleting]     = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await skillsApi.list();
      setSkills(data);
    } catch {
      toast.error('Lỗi tải danh sách skills');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await skillsApi.delete(deleteTarget.id);
      toast.success('Đã xóa skill');
      setDeleteTarget(null);
      load();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Lỗi khi xóa');
    } finally {
      setDeleting(false);
    }
  };

  const filtered = skills.filter(s => {
    const q = search.toLowerCase();
    const matchSearch = !search || s.name.toLowerCase().includes(q) || s.normalized_name.includes(q);
    const matchCat    = !catFilter || s.category === catFilter;
    return matchSearch && matchCat;
  });

  // Group stats
  const catCounts = skills.reduce<Record<string, number>>((acc, s) => {
    acc[s.category] = (acc[s.category] || 0) + 1;
    return acc;
  }, {});
  const topCat = Object.entries(catCounts).sort((a, b) => b[1] - a[1])[0];

  return (
    <>
      {/* Stats */}
      <div className="admin-stats">
        <div className="admin-stat-card">
          <div className="admin-stat-icon"><Wrench size={20} /></div>
          <div><p>Tổng số Skills</p><strong>{skills.length}</strong></div>
        </div>
        <div className="admin-stat-card">
          <div className="admin-stat-icon" style={{ background: 'rgba(6,182,212,0.15)', color: 'var(--brand-accent)' }}>
            <Database size={20} />
          </div>
          <div><p>Số danh mục</p><strong>{Object.keys(catCounts).length}</strong></div>
        </div>
        {topCat && (
          <div className="admin-stat-card">
            <div className="admin-stat-icon" style={{ background: 'rgba(139,92,246,0.15)', color: 'var(--brand-secondary)' }}>
              <BookOpen size={20} />
            </div>
            <div>
              <p>Nhiều nhất</p>
              <strong style={{ fontSize: '0.95rem' }}>{topCat[0].replace(/_/g, ' ')} ({topCat[1]})</strong>
            </div>
          </div>
        )}
      </div>

      {/* Toolbar */}
      <div className="admin-toolbar">
        <div className="admin-search">
          <Search size={16} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
          <input
            placeholder="Tìm theo tên skill..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <select className="filter-select" value={catFilter} onChange={e => setCatFilter(e.target.value)}>
          <option value="">Tất cả danh mục</option>
          {SKILL_CATS.map(c => <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>)}
        </select>
        <button className="btn btn-ghost" onClick={load} title="Làm mới">
          <RefreshCw size={16} />
        </button>
        <button className="btn btn-primary" onClick={() => setModalSkill(null)}>
          <Plus size={16} /> Thêm Skill
        </button>
      </div>

      {/* Table */}
      <div className="admin-table-wrap">
        {loading ? (
          <div className="admin-empty">
            <Loader2 size={36} className="animate-spin" style={{ color: 'var(--brand-primary)' }} />
            <p style={{ marginTop: 16 }}>Đang tải...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="admin-empty">
            <Wrench size={48} />
            <h3>Chưa có skill nào</h3>
            <p>Nhấn "+ Thêm Skill" để bắt đầu</p>
          </div>
        ) : (
          <table className="admin-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Tên</th>
                <th>Normalized</th>
                <th>Danh mục</th>
                <th>Mô tả</th>
                <th>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(skill => (
                <tr key={skill.id}>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>#{skill.id}</td>
                  <td style={{ fontWeight: 600 }}>{skill.name}</td>
                  <td>
                    <code style={{ fontSize: '0.78rem', color: 'var(--brand-accent)', background: 'rgba(6,182,212,0.08)', padding: '2px 6px', borderRadius: 4 }}>
                      {skill.normalized_name}
                    </code>
                  </td>
                  <td><CatBadge cat={skill.category} /></td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {skill.description || <span style={{ color: 'var(--text-muted)' }}>—</span>}
                  </td>
                  <td>
                    <div className="admin-table-actions">
                      <button className="icon-btn" onClick={() => setModalSkill(skill)} title="Sửa">
                        <Pencil size={14} />
                      </button>
                      <button className="icon-btn danger" onClick={() => setDeleteTarget(skill)} title="Xóa">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Modals */}
      {modalSkill !== undefined && (
        <SkillModal
          skill={modalSkill}
          onClose={() => setModalSkill(undefined)}
          onSaved={load}
        />
      )}
      {deleteTarget && (
        <ConfirmModal
          label={deleteTarget.name}
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
          loading={deleting}
        />
      )}
    </>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
function AdminCvsTab() {
  const [cvs, setCvs] = useState<CV[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCv, setSelectedCv] = useState<CV | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setCvs(await adminApi.cvs());
    } catch {
      toast.error('Không thể tải danh sách CV');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const remove = async (id: number) => {
    if (!window.confirm('Xóa CV này khỏi hệ thống?')) return;
    try {
      await adminApi.deleteCv(id);
      toast.success('Đã xóa CV');
      load();
    } catch {
      toast.error('Không thể xóa CV');
    }
  };

  return (
    <>
      <div className="admin-table-wrap">
        <div className="admin-toolbar">
          <strong>CV người dùng ({cvs.length})</strong>
          <button className="btn btn-ghost" onClick={load}>
            <RefreshCw size={16} /> Làm mới
          </button>
        </div>
        {loading ? (
          <div className="admin-empty">
            <Loader2 className="animate-spin text-brand" size={32} />
          </div>
        ) : (
          <table className="admin-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>File</th>
                <th>User ID</th>
                <th>Trạng thái</th>
                <th>Ngày tải</th>
                <th>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {cvs.map(cv => (
                <tr
                  key={cv.id}
                  className="clickable-row"
                  tabIndex={0}
                  onClick={() => setSelectedCv(cv)}
                  onKeyDown={e => e.key === 'Enter' && setSelectedCv(cv)}
                >
                  <td style={{ color: 'var(--text-muted)' }}>#{cv.id}</td>
                  <td>
                    <strong>{cv.filename}</strong>
                    <div className="row-hint text-xs text-brand mt-1" style={{ opacity: 0.8 }}>Nhấn để xem chi tiết</div>
                  </td>
                  <td>{cv.user_id}</td>
                  <td>
                    <span className={`status-text ${cv.status}`}>{cv.status}</span>
                  </td>
                  <td style={{ color: 'var(--text-muted)' }}>{new Date(cv.created_at).toLocaleString('vi-VN')}</td>
                  <td>
                    <button
                      className="icon-btn danger"
                      onClick={e => { e.stopPropagation(); remove(cv.id); }}
                      title="Xóa"
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {selectedCv && <CandidateDetail cv={selectedCv} onClose={() => setSelectedCv(null)} />}
    </>
  );
}

function CandidateDetail({ cv, onClose }: { cv: CV; onClose: () => void }) {
  const a = cv.ai_analysis;
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-panel candidate-detail" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <p className="section-kicker" style={{ fontSize: '0.7rem', color: 'var(--brand-primary)', fontWeight: 700, letterSpacing: '0.05em', marginBottom: 4 }}>CHI TIẾT ỨNG VIÊN</p>
            <h3 style={{ margin: 0, fontSize: '1.25rem' }}>{a?.full_name || cv.filename}</h3>
          </div>
          <button className="modal-close" onClick={onClose}><X size={16} /></button>
        </div>
        <div className="modal-body">
          <div className="candidate-meta" style={{ display: 'flex', gap: 12, marginBottom: 16, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            <span>CV #{cv.id}</span>
            <span>&bull;</span>
            <span>User #{cv.user_id}</span>
            <span>&bull;</span>
            <span className={`status-text ${cv.status}`}>{cv.status}</span>
          </div>
          {a ? (
            <>
              <p className="candidate-summary" style={{ lineHeight: 1.6, color: 'var(--text-primary)', marginBottom: 20 }}>
                {a.summary || 'Chưa có phần tóm tắt.'}
              </p>
              <div className="candidate-contact" style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 20, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                <span><strong>Email:</strong> {a.email || '—'}</span>
                <span><strong>SĐT:</strong> {a.phone || '—'}</span>
                <span><strong>Địa điểm:</strong> {a.location || '—'}</span>
              </div>
              <h4 style={{ marginBottom: 12, fontSize: '1rem' }}>Kỹ năng nổi bật</h4>
              <div className="candidate-skills" style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {(a.skills || []).map((skill, i) => (
                  <span key={i} style={{ padding: '4px 10px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--bg-border)', borderRadius: 'var(--radius-full)', fontSize: '0.8rem' }}>
                    {skill.name}
                  </span>
                ))}
              </div>
            </>
          ) : (
            <div className="detail-empty" style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>
              CV chưa có dữ liệu phân tích chi tiết.
            </div>
          )}
        </div>
        <div className="modal-footer" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span className="detail-date" style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Tải lên {new Date(cv.created_at).toLocaleString('vi-VN')}
          </span>
          <button className="btn btn-ghost" onClick={onClose}>Đóng</button>
        </div>
      </div>
    </div>
  );
}

function AdminUsersTab() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [search, setSearch] = useState('');
  const currentUser = useAuthStore(state => state.user);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(false);
    try {
      setUsers(await adminApi.users());
    } catch {
      setLoadError(true);
      toast.error('Không thể tải danh sách người dùng');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const toggleActive = async (user: User) => {
    try {
      await adminApi.updateUserActive(user.id, !user.is_active);
      toast.success(user.is_active ? 'Đã khóa tài khoản' : 'Đã mở khóa tài khoản');
      await load();
    } catch (error: unknown) {
      const detail = isAxiosError(error) ? error.response?.data?.detail : undefined;
      toast.error(typeof detail === 'string' ? detail : 'Không thể cập nhật tài khoản');
    }
  };

  const filtered = users.filter(user =>
    `${user.full_name} ${user.email}`.toLowerCase().includes(search.toLowerCase()),
  );
  const activeCount = users.filter(user => user.is_active).length;

  return (
    <>
      <div className="admin-stats">
        <div className="admin-stat-card">
          <div className="admin-stat-icon"><Users size={20} /></div>
          <div><p>Tổng người dùng</p><strong>{users.length}</strong></div>
        </div>
        <div className="admin-stat-card">
          <div className="admin-stat-icon"><UserCheck size={20} /></div>
          <div><p>Đang hoạt động</p><strong>{activeCount}</strong></div>
        </div>
      </div>
      <div className="admin-toolbar">
        <div className="admin-search">
          <Search size={16} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
          <input aria-label="Tìm người dùng" placeholder="Tìm theo tên hoặc email..." value={search} onChange={event => setSearch(event.target.value)} />
        </div>
        <button className="btn btn-ghost" onClick={load} title="Làm mới" disabled={loading}><RefreshCw size={16} /></button>
      </div>
      <div className="admin-table-wrap">
        {loading ? (
          <div className="admin-empty"><Loader2 size={36} className="animate-spin" style={{ color: 'var(--brand-primary)' }} /></div>
        ) : loadError ? (
          <div className="admin-empty">
            <AlertTriangle size={36} />
            <h3>Không thể tải danh sách người dùng</h3>
            <button className="btn btn-ghost" onClick={load}><RefreshCw size={16} /> Thử lại</button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="admin-empty"><Users size={40} /><h3>{search ? 'Không tìm thấy người dùng' : 'Chưa có người dùng'}</h3></div>
        ) : (
          <table className="admin-table">
            <thead><tr><th>ID</th><th>Người dùng</th><th>Quyền</th><th>Trạng thái</th><th>Ngày tạo</th><th>Thao tác</th></tr></thead>
            <tbody>
              {filtered.map(user => (
                <tr key={user.id}>
                  <td style={{ color: 'var(--text-muted)' }}>#{user.id}</td>
                  <td><strong>{user.full_name}</strong><div className="row-hint">{user.email}</div></td>
                  <td>{user.role === 'admin' ? 'Admin' : 'Người dùng'}</td>
                  <td><span className={`status-text ${user.is_active ? 'analyzed' : 'failed'}`}>{user.is_active ? 'Hoạt động' : 'Đã khóa'}</span></td>
                  <td style={{ color: 'var(--text-muted)' }}>{new Date(user.created_at).toLocaleDateString('vi-VN')}</td>
                  <td>
                    <button className={`btn ${user.is_active ? 'btn-danger' : 'btn-secondary'}`} onClick={() => toggleActive(user)} disabled={user.id === currentUser?.id || loading} title={user.id === currentUser?.id ? 'Không thể tự khóa tài khoản' : undefined}>
                      {user.is_active ? <UserX size={15} /> : <UserCheck size={15} />}{user.is_active ? 'Khóa' : 'Mở khóa'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

// Main AdminPage
// ──────────────────────────────────────────────────────────────────────────────
export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<AdminTab>('cvs');

  return (
    <div className="admin-page animate-fade-in">
      {/* Header */}
      <div className="admin-header">
        <div className="admin-header-left">
          <h2>Bảng điều khiển Admin</h2>
          <p>Quản lý tài khoản, CV, Jobs và Skills</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.3)', borderRadius: 'var(--radius-md)', padding: '6px 14px', fontSize: '0.8rem', color: 'var(--brand-primary)' }}>
          <ShieldCheck size={14} />
          <span>Chế độ Admin</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="admin-tabs">
        <button
          className={`admin-tab ${activeTab === 'jobs' ? 'active' : ''}`}
          onClick={() => setActiveTab('jobs')}
        >
          <Briefcase size={16} /> Quản lý Jobs
        </button>
        <button className={`admin-tab ${activeTab === 'cvs' ? 'active' : ''}`} onClick={() => setActiveTab('cvs')}>
          <FileText size={16} /> Quản lý CV
        </button>
        <button
          className={`admin-tab ${activeTab === 'skills' ? 'active' : ''}`}
          onClick={() => setActiveTab('skills')}
        >
          <Wrench size={16} /> Quản lý Skills
        </button>
        <button className={`admin-tab ${activeTab === 'users' ? 'active' : ''}`} onClick={() => setActiveTab('users')}>
          <Users size={16} /> Người dùng
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'jobs' ? <JobsTab /> : activeTab === 'skills' ? <SkillsTab /> : activeTab === 'users' ? <AdminUsersTab /> : <AdminCvsTab />}
    </div>
  );
}
