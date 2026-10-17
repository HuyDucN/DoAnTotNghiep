import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { isAxiosError } from 'axios';
import { jobsApi, skillsApi, adminApi, getApiErrorMessage } from '../../services/api';
import type { Job, Skill, CV, User, JobSkillInput, PaginatedResponse, AdminJobListResponse, AdminUserListResponse } from '../../types';
import { useAuthStore } from '../../store/authStore';
import { syncCvDeleted } from '../../services/cvCache';
import QueryLoadNotice from '../../components/QueryLoadNotice';
import {
  Briefcase, Wrench, Plus, Pencil, Trash2, X, Search,
  Loader2, AlertTriangle, ShieldCheck, BookOpen, Database,
  Save, RefreshCw, FileText, Users, UserCheck, UserX,
  ChevronLeft, ChevronRight, Sparkles
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useForm, useWatch } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import './AdminPage.css';

// ------------------------------------------------------------------------------
// Constants
// ------------------------------------------------------------------------------
const JOB_TYPES  = ['full_time', 'part_time', 'internship', 'freelance'];
const JOB_LEVELS = ['intern', 'junior', 'mid', 'senior', 'lead'];
const JOB_CATS   = [
  'backend', 'frontend', 'fullstack', 'data', 'ai_ml', 'devops',
  'mobile', 'qa', 'other',
];
const SKILL_CATS = [
  'programming_language', 'framework', 'database',
  'cloud', 'devops', 'ai_ml', 'soft_skill', 'tool', 'other',
];
const IMPORTANCE_OPTS: Array<'high' | 'medium' | 'low'> = ['high', 'medium', 'low'];

// ------------------------------------------------------------------------------
// Sub-types
// ------------------------------------------------------------------------------
type AdminTab = 'jobs' | 'skills' | 'cvs' | 'users';

const jobSkillSchema = z.object({
  skill_name: z.string().trim().min(1, 'Tên kỹ năng không được để trống'),
  is_required: z.boolean(),
  importance: z.enum(['high', 'medium', 'low']),
});

const jobFormSchema = z.object({
  title: z.string().trim().min(1, 'Tiêu đề job không được để trống').max(255, 'Tiêu đề job quá dài'),
  company: z.string().max(255, 'Tên công ty quá dài'),
  location: z.string().max(255, 'Địa điểm quá dài'),
  job_type: z.enum(['full_time', 'part_time', 'internship', 'freelance']),
  level: z.enum(['intern', 'junior', 'mid', 'senior', 'lead']),
  category: z.enum(['backend', 'frontend', 'fullstack', 'data', 'ai_ml', 'devops', 'mobile', 'qa', 'other']),
  description: z.string().max(5000, 'Mô tả không được quá 5.000 ký tự'),
  salary_min: z.string().refine((value) => !value || (/^\d+$/.test(value) && Number(value) >= 0), 'Lương phải là số nguyên không âm'),
  salary_max: z.string().refine((value) => !value || (/^\d+$/.test(value) && Number(value) >= 0), 'Lương phải là số nguyên không âm'),
  required_skills: z.array(jobSkillSchema),
  preferred_skills: z.array(jobSkillSchema),
}).superRefine((data, ctx) => {
  if (data.salary_min && data.salary_max && Number(data.salary_min) > Number(data.salary_max)) {
    ctx.addIssue({ code: 'custom', path: ['salary_max'], message: 'Lương đến phải lớn hơn hoặc bằng lương từ' });
  }
});

const skillFormSchema = z.object({
  name: z.string().trim().min(1, 'Tên kỹ năng không được để trống').max(255, 'Tên kỹ năng quá dài'),
  category: z.enum(['programming_language', 'framework', 'database', 'cloud', 'devops', 'ai_ml', 'soft_skill', 'tool', 'other']),
  description: z.string().max(2000, 'Mô tả không được quá 2.000 ký tự'),
});

type JobFormData = z.infer<typeof jobFormSchema>;
type SkillFormData = z.infer<typeof skillFormSchema>;

const defaultJobForm = (): JobFormData => ({
  title: '', company: '', location: '',
  job_type: 'full_time', level: 'junior', category: 'backend',
  description: '', salary_min: '', salary_max: '',
  required_skills: [], preferred_skills: [],
});

const defaultSkillForm = (): SkillFormData => ({
  name: '', category: 'other', description: '',
});

// ------------------------------------------------------------------------------
// Helper components
// ------------------------------------------------------------------------------

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

// ------------------------------------------------------------------------------
// Confirm Delete Modal
// ------------------------------------------------------------------------------
interface ConfirmModalProps {
  label: string;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
}

function ConfirmModal({ label, onConfirm, onCancel, loading }: ConfirmModalProps) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !loading) onCancel();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [loading, onCancel]);

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div
        className="modal-panel modal-sm"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-delete-title"
        aria-describedby="confirm-delete-description"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <h3 id="confirm-delete-title">Xác nhận xóa</h3>
          <button type="button" className="modal-close" onClick={onCancel} aria-label="Đóng hộp thoại">
            <X size={16} />
          </button>
        </div>
        <div className="modal-body">
          <div className="confirm-body">
            <div className="confirm-icon"><AlertTriangle size={28} /></div>
            <h4>Bạn có chắc chắn muốn xóa?</h4>
            <p id="confirm-delete-description" className="mt-2">
              <strong style={{ color: 'var(--text-primary)' }}>{label}</strong> sẽ bị xóa
              vĩnh viễn và không thể khôi phục.
            </p>
          </div>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-ghost" onClick={onCancel} disabled={loading}>Hủy</button>
          <button type="button" className="btn btn-danger" onClick={onConfirm} disabled={loading}>
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={16} />}
            Xóa
          </button>
        </div>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------------------
// Skill Row Builder (inside Job modal)
// ------------------------------------------------------------------------------
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

// ------------------------------------------------------------------------------
// Job Modal
// ------------------------------------------------------------------------------
interface JobModalProps {
  job: Job | null; // null = create mode
  onClose: () => void;
  onSaved: () => void;
}

function JobModal({ job, onClose, onSaved }: JobModalProps) {
  const isEdit = !!job;
  const initialForm: JobFormData = job
    ? {
        title: job.title,
        company: job.company || '',
        location: job.location || '',
        job_type: job.job_type as JobFormData['job_type'],
        level: job.level as JobFormData['level'],
        category: job.category as JobFormData['category'],
        description: job.description || '',
        salary_min: job.salary_min?.toString() || '',
        salary_max: job.salary_max?.toString() || '',
        required_skills: job.job_skills.filter((skill) => skill.is_required).map((skill) => ({
          skill_name: skill.skill_name,
          is_required: true,
          importance: skill.importance,
        })),
        preferred_skills: job.job_skills.filter((skill) => !skill.is_required).map((skill) => ({
          skill_name: skill.skill_name,
          is_required: false,
          importance: skill.importance,
        })),
      }
    : defaultJobForm();

  const {
    register,
    handleSubmit,
    control: jobControl,
    setValue,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<JobFormData>({
    resolver: zodResolver(jobFormSchema),
    defaultValues: initialForm,
  });

  const requiredSkills = useWatch({ control: jobControl, name: 'required_skills' });
  const preferredSkills = useWatch({ control: jobControl, name: 'preferred_skills' });
  const descriptionValue = useWatch({ control: jobControl, name: 'description' });

  const parseDescriptionMutation = useMutation({
    mutationFn: (description: string) => jobsApi.parseDescription(description),
    onSuccess: (data) => {
      if (data.title) setValue('title', data.title, { shouldDirty: true });
      if (data.company) setValue('company', data.company, { shouldDirty: true });
      if (data.location) setValue('location', data.location, { shouldDirty: true });
      if (data.job_type) setValue('job_type', data.job_type, { shouldDirty: true });
      if (data.level) setValue('level', data.level, { shouldDirty: true });
      if (data.category) setValue('category', data.category, { shouldDirty: true });
      if (data.salary_min != null) setValue('salary_min', String(data.salary_min), { shouldDirty: true });
      if (data.salary_max != null) setValue('salary_max', String(data.salary_max), { shouldDirty: true });
      setValue('required_skills', data.required_skills ?? [], { shouldDirty: true, shouldValidate: true });
      setValue('preferred_skills', data.preferred_skills ?? [], { shouldDirty: true, shouldValidate: true });
      toast.success('Đã bóc tách JD và điền vào biểu mẫu.');
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Không thể bóc tách JD.'),
  });

  const updateSkills = (field: 'required_skills' | 'preferred_skills', skills: JobSkillInput[]) => {
    setValue(field, skills as JobFormData[typeof field], { shouldDirty: true, shouldValidate: true });
  };

  const onSubmit = async (formData: JobFormData) => {
    const payload = {
      title: formData.title.trim(),
      company: formData.company.trim() || null,
      location: formData.location.trim() || null,
      job_type: formData.job_type,
      level: formData.level,
      category: formData.category,
      description: formData.description.trim() || null,
      salary_min: formData.salary_min ? Number(formData.salary_min) : null,
      salary_max: formData.salary_max ? Number(formData.salary_max) : null,
      required_skills: formData.required_skills,
      preferred_skills: formData.preferred_skills,
    };

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
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-panel" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <h3>{isEdit ? '✏️ Sửa Job' : '➕ Tạo Job mới'}</h3>
          <button className="modal-close" onClick={onClose} type="button"><X size={16} /></button>
        </div>
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <div className="modal-body">
            <div className="form-grid">
              <div className="form-group form-span-2">
                <label className="form-label">Tiêu đề <span style={{ color: 'var(--color-danger)' }}>*</span></label>
                <input className={'form-input ' + (errors.title ? 'input-error' : '')} placeholder="Vd: Senior Backend Developer" aria-invalid={Boolean(errors.title)} {...register('title')} />
                {errors.title && <p className="form-error">{errors.title.message}</p>}
              </div>
              <div className="form-group">
                <label className="form-label">Công ty</label>
                <input className={'form-input ' + (errors.company ? 'input-error' : '')} placeholder="Tên công ty" {...register('company')} />
                {errors.company && <p className="form-error">{errors.company.message}</p>}
              </div>
              <div className="form-group">
                <label className="form-label">Địa điểm</label>
                <input className={'form-input ' + (errors.location ? 'input-error' : '')} placeholder="Vd: Hà Nội, Remote..." {...register('location')} />
                {errors.location && <p className="form-error">{errors.location.message}</p>}
              </div>
              <div className="form-group">
                <label className="form-label">Loại hình</label>
                <select className="form-input" {...register('job_type')}>
                  {JOB_TYPES.map((type) => <option key={type} value={type}>{type.replace('_', ' ')}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Cấp độ</label>
                <select className="form-input" {...register('level')}>
                  {JOB_LEVELS.map((level) => <option key={level} value={level}>{level}</option>)}
                </select>
              </div>
              <div className="form-group form-span-2">
                <label className="form-label">Danh mục</label>
                <select className="form-input" {...register('category')}>
                  {JOB_CATS.map((category) => <option key={category} value={category}>{category.replace(/_/g, ' ')}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Lương từ (USD)</label>
                <input className={'form-input ' + (errors.salary_min ? 'input-error' : '')} type="number" min={0} placeholder="0" {...register('salary_min')} />
                {errors.salary_min && <p className="form-error">{errors.salary_min.message}</p>}
              </div>
              <div className="form-group">
                <label className="form-label">Lương đến (USD)</label>
                <input className={'form-input ' + (errors.salary_max ? 'input-error' : '')} type="number" min={0} placeholder="0" {...register('salary_max')} />
                {errors.salary_max && <p className="form-error">{errors.salary_max.message}</p>}
              </div>
              <div className="form-group form-span-2">
                <label className="form-label">Mô tả công việc</label>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                  <span className="text-muted text-xs">AI có thể điền các trường từ JD</span>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => parseDescriptionMutation.mutate(getValues('description'))}
                    disabled={parseDescriptionMutation.isPending || descriptionValue.trim().length < 20}
                  >
                    {parseDescriptionMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                    {parseDescriptionMutation.isPending ? 'Đang bóc tách...' : 'Bóc tách JD bằng AI'}
                  </button>
                </div>                <textarea className={'form-input ' + (errors.description ? 'input-error' : '')} rows={4} placeholder="Mô tả chi tiết về vị trí, trách nhiệm..." style={{ resize: 'vertical' }} {...register('description')} />
                {errors.description && <p className="form-error">{errors.description.message}</p>}
              </div>
              <SkillBuilder label="Kỹ năng bắt buộc (Required)" type="required" skills={requiredSkills} onChange={(skills) => updateSkills('required_skills', skills)} />
              <SkillBuilder label="Kỹ năng ưu tiên (Preferred)" type="preferred" skills={preferredSkills} onChange={(skills) => updateSkills('preferred_skills', skills)} />
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-ghost" onClick={onClose} disabled={isSubmitting}>Hủy</button>
            <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
              {isSubmitting ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
              {isEdit ? 'Cập nhật' : 'Tạo Job'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

interface SkillModalProps {
  skill: Skill | null;
  onClose: () => void;
  onSaved: () => void;
}

function SkillModal({ skill, onClose, onSaved }: SkillModalProps) {
  const isEdit = !!skill;
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SkillFormData>({
    resolver: zodResolver(skillFormSchema),
    defaultValues: skill
      ? { name: skill.name, category: skill.category as SkillFormData['category'], description: skill.description || '' }
      : defaultSkillForm(),
  });

  const onSubmit = async (formData: SkillFormData) => {
    const payload = {
      name: formData.name.trim(),
      category: formData.category,
      description: formData.description.trim() || undefined,
    };
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
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-panel modal-sm" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <h3>{isEdit ? '✏️ Sửa Skill' : '➕ Thêm Skill'}</h3>
          <button className="modal-close" onClick={onClose} type="button"><X size={16} /></button>
        </div>
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <div className="modal-body">
            <div className="form-grid one-col">
              <div className="form-group">
                <label className="form-label">Tên kỹ năng <span style={{ color: 'var(--color-danger)' }}>*</span></label>
                <input className={'form-input ' + (errors.name ? 'input-error' : '')} placeholder="Vd: Python, React, Docker..." aria-invalid={Boolean(errors.name)} {...register('name')} />
                {errors.name && <p className="form-error">{errors.name.message}</p>}
              </div>
              <div className="form-group">
                <label className="form-label">Danh mục</label>
                <select className="form-input" {...register('category')}>
                  {SKILL_CATS.map((category) => <option key={category} value={category}>{category.replace(/_/g, ' ')}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Mô tả (tùy chọn)</label>
                <textarea className={'form-input ' + (errors.description ? 'input-error' : '')} rows={3} placeholder="Mô tả ngắn về kỹ năng..." style={{ resize: 'vertical' }} {...register('description')} />
                {errors.description && <p className="form-error">{errors.description.message}</p>}
              </div>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-ghost" onClick={onClose} disabled={isSubmitting}>Hủy</button>
            <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
              {isSubmitting ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
              {isEdit ? 'Cập nhật' : 'Thêm Skill'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function JobsTab() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [catFilter, setCatFilter] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [modalJob, setModalJob] = useState<Job | null | undefined>(undefined);
  const [deleteTarget, setDeleteTarget] = useState<Job | null>(null);

  const params = {
    page: currentPage, size: 20,
    search: search.trim() || undefined, category: catFilter || undefined,
  };
  const jobsQuery = useQuery<AdminJobListResponse>({
    queryKey: ['admin', 'jobs', params],
    queryFn: () => jobsApi.listAdmin(params),
  });
  const jobs = jobsQuery.data?.items ?? [];
  const pagination = jobsQuery.data ?? {
    total: 0, page: currentPage, size: 20, pages: 1, active_total: 0, category_count: 0,
  };
  const loading = jobsQuery.isPending;
  const invalidateJobs = () => Promise.all([
    queryClient.invalidateQueries({ queryKey: ['admin', 'jobs'] }),
    queryClient.invalidateQueries({ queryKey: ['jobs'] }),
  ]);
  const load = () => { void invalidateJobs(); };

  const deleteMutation = useMutation({
    mutationFn: (id: number) => jobsApi.delete(id),
    onSuccess: async () => {
      toast.success('Đã xóa job');
      setDeleteTarget(null);
      await invalidateJobs();
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Lỗi khi xóa'),
  });
  const deleting = deleteMutation.isPending;
  const handleDelete = () => {
    if (deleteTarget) deleteMutation.mutate(deleteTarget.id);
  };

  return (
    <>
      {/* Stats */}
      <div className="admin-stats">
        <div className="admin-stat-card">
          <div className="admin-stat-icon"><Briefcase size={20} /></div>
          <div><p>{search.trim() || catFilter ? 'Jobs phù hợp bộ lọc' : 'Tổng số Jobs'}</p><strong>{loading || jobsQuery.isError ? '—' : pagination.total}</strong></div>
        </div>
        <div className="admin-stat-card">
          <div className="admin-stat-icon" style={{ background: 'rgba(16,185,129,0.15)', color: 'var(--color-success)' }}>
            <ShieldCheck size={20} />
          </div>
          <div><p>Đang hoạt động</p><strong>{loading || jobsQuery.isError ? '—' : pagination.active_total}</strong></div>
        </div>
        <div className="admin-stat-card">
          <div className="admin-stat-icon" style={{ background: 'rgba(245,158,11,0.15)', color: 'var(--color-warning)' }}>
            <BookOpen size={20} />
          </div>
          <div><p>Danh mục</p><strong>{loading || jobsQuery.isError ? '—' : pagination.category_count}</strong></div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="admin-toolbar">
        <div className="admin-search">
          <Search size={16} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
          <input
            placeholder="Tìm theo tiêu đề, công ty..."
            value={search}
            onChange={e => { setSearch(e.target.value); setCurrentPage(1); }}
          />
        </div>
        <select className="filter-select" value={catFilter} onChange={e => { setCatFilter(e.target.value); setCurrentPage(1); }}>
          <option value="">Tất cả danh mục</option>
          {JOB_CATS.map(c => <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>)}
        </select>
        <button className="btn btn-ghost" onClick={load} title="Làm mới" disabled={jobsQuery.isFetching}>
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
        ) : jobsQuery.isError ? (
          <div className="admin-empty">
            <AlertTriangle size={40} />
            <h3>Không thể tải danh sách công việc</h3>
            <button className="btn btn-ghost" onClick={load}><RefreshCw size={16} /> Thử lại</button>
          </div>
        ) : jobs.length === 0 ? (
          <div className="admin-empty">
            <Briefcase size={48} />
            <h3>{search.trim() || catFilter ? 'Không tìm thấy job phù hợp' : 'Chưa có job nào'}</h3>
            <p>{search.trim() || catFilter ? 'Hãy thay đổi từ khóa hoặc danh mục.' : 'Nhấn "+ Tạo Job" để bắt đầu'}</p>
          </div>
        ) : (
          <table className="admin-table">
            <thead>
              <tr>
                <th>STT</th>
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
              {jobs.map((job, index) => (
                <tr key={job.id}>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{(pagination.page - 1) * pagination.size + index + 1}</td>
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

      {!loading && !jobsQuery.isError && pagination.pages > 1 && (
        <div className="pagination-controls" style={{ padding: '20px' }}>
          <button className="btn btn-ghost btn-sm" onClick={() => setCurrentPage(pagination.page - 1)} disabled={pagination.page <= 1 || jobsQuery.isFetching}>
            <ChevronLeft size={16} /> Trước
          </button>
          <span className="pagination-info text-muted text-xs">Trang {pagination.page} / {pagination.pages} · {pagination.total} công việc</span>
          <button className="btn btn-ghost btn-sm" onClick={() => setCurrentPage(pagination.page + 1)} disabled={pagination.page >= pagination.pages || jobsQuery.isFetching}>
            Sau <ChevronRight size={16} />
          </button>
        </div>
      )}

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

// ------------------------------------------------------------------------------
// Skills Tab
// ------------------------------------------------------------------------------
function SkillsTab() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [catFilter, setCatFilter] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [modalSkill, setModalSkill] = useState<Skill | null | undefined>(undefined);
  const [deleteTarget, setDeleteTarget] = useState<Skill | null>(null);

  const skillsQuery = useQuery<PaginatedResponse<Skill>>({
    queryKey: ['admin', 'skills', currentPage, catFilter, search],
    queryFn: () => skillsApi.list({
      page: currentPage,
      size: 20,
      category: catFilter || undefined,
      search: search.trim() || undefined,
    }),
  });
  const skills = skillsQuery.data?.items ?? [];
  const pagination = skillsQuery.data ?? { total: 0, page: currentPage, size: 20, pages: 1 };
  const loading = skillsQuery.isPending;
  const load = () => { void queryClient.invalidateQueries({ queryKey: ['admin', 'skills', currentPage] }); };

  const deleteMutation = useMutation({
    mutationFn: (id: number) => skillsApi.delete(id),
    onSuccess: async () => {
      toast.success('Đã xóa skill');
      setDeleteTarget(null);
      await queryClient.invalidateQueries({ queryKey: ['admin', 'skills'] });
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Lỗi khi xóa'),
  });
  const deleting = deleteMutation.isPending;
  const handleDelete = () => {
    if (deleteTarget) deleteMutation.mutate(deleteTarget.id);
  };

  const filtered = skills;

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
          <div><p>Tổng số Skills</p><strong>{skillsQuery.data === undefined ? '—' : pagination.total}</strong></div>
        </div>
        <div className="admin-stat-card">
          <div className="admin-stat-icon" style={{ background: 'rgba(6,182,212,0.15)', color: 'var(--brand-accent)' }}>
            <Database size={20} />
          </div>
          <div><p>Số danh mục</p><strong>{skillsQuery.data === undefined ? '—' : Object.keys(catCounts).length}</strong></div>
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
            onChange={e => { setSearch(e.target.value); setCurrentPage(1); }}
          />
        </div>
        <select className="filter-select" value={catFilter} onChange={e => { setCatFilter(e.target.value); setCurrentPage(1); }}>
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

      <QueryLoadNotice query={skillsQuery} label="danh sách kỹ năng" />

      {/* Table */}
      <div className="admin-table-wrap">
        {loading ? (
          <div className="admin-empty">
            <Loader2 size={36} className="animate-spin" style={{ color: 'var(--brand-primary)' }} />
            <p style={{ marginTop: 16 }}>Đang tải...</p>
          </div>
        ) : skillsQuery.isError ? null : filtered.length === 0 ? (
          <div className="admin-empty">
            <Wrench size={48} />
            <h3>Chưa có skill nào</h3>
            <p>Nhấn "+ Thêm Skill" để bắt đầu</p>
          </div>
        ) : (
          <table className="admin-table">
            <thead>
              <tr>
                <th>STT</th>
                <th>Tên</th>
                <th>Normalized</th>
                <th>Danh mục</th>
                <th>Mô tả</th>
                <th>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((skill, index) => (
                <tr key={skill.id}>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{(pagination.page - 1) * pagination.size + index + 1}</td>
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
        {!loading && skillsQuery.isSuccess && pagination.pages > 1 && (
          <div className="pagination-controls" style={{ padding: '20px' }}>
            <button className="btn btn-ghost btn-sm" onClick={() => setCurrentPage((page) => Math.max(1, page - 1))} disabled={currentPage <= 1}>
              <ChevronLeft size={16} /> Trước
            </button>
            <span className="pagination-info text-muted text-xs">{currentPage} / {pagination.pages}</span>
            <button className="btn btn-ghost btn-sm" onClick={() => setCurrentPage((page) => Math.min(pagination.pages, page + 1))} disabled={currentPage >= pagination.pages}>
              Sau <ChevronRight size={16} />
            </button>
          </div>
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

// ------------------------------------------------------------------------------
function AdminCvsTab() {
  const queryClient = useQueryClient();
  const [selectedCv, setSelectedCv] = useState<CV | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const cvsQuery = useQuery<PaginatedResponse<CV>>({
    queryKey: ['admin', 'cvs', currentPage],
    queryFn: () => adminApi.cvs({ page: currentPage, size: 20 }),
  });
  const cvs = cvsQuery.data?.items ?? [];
  const pagination = cvsQuery.data ?? { total: 0, page: currentPage, size: 20, pages: 1 };
  const loading = cvsQuery.isPending;
  const removeMutation = useMutation({
    mutationFn: (id: number) => adminApi.deleteCv(id),
    onSuccess: async (_, deletedId) => {
      toast.success('Đã xóa CV');
      if (selectedCv?.id === deletedId) setSelectedCv(null);
      await syncCvDeleted(queryClient, deletedId);
    },
    onError: (error: unknown) => toast.error(getApiErrorMessage(error, 'Không thể xóa CV')),
  });
  const load = () => { void queryClient.invalidateQueries({ queryKey: ['admin', 'cvs', currentPage] }); };
  const remove = (id: number) => {
    if (window.confirm('Xóa CV này khỏi hệ thống?')) removeMutation.mutate(id);
  };

  return (
    <>
      <div className="admin-table-wrap">
        <div className="admin-toolbar">
          <strong>CV người dùng ({cvsQuery.data === undefined ? '—' : pagination.total})</strong>
          <button className="btn btn-ghost" onClick={load} disabled={loading}><RefreshCw size={16} /> Làm mới</button>
        </div>
        <QueryLoadNotice query={cvsQuery} label="danh sách CV quản trị" />
        {loading ? (
          <div className="admin-empty"><Loader2 className="animate-spin text-brand" size={32} /></div>
        ) : cvsQuery.isError ? null : cvsQuery.isSuccess && cvs.length === 0 ? (
          <div className="admin-empty"><FileText size={40} /><h3>Chưa có CV nào</h3></div>
        ) : (
          <table className="admin-table">
            <thead><tr><th>STT</th><th>File</th><th>User ID</th><th>Trạng thái</th><th>Ngày tải</th><th>Thao tác</th></tr></thead>
            <tbody>
              {cvs.map((cv, index) => (
                <tr key={cv.id} className="clickable-row" tabIndex={0} onClick={() => setSelectedCv(cv)} onKeyDown={(event) => event.key === 'Enter' && setSelectedCv(cv)}>
                  <td style={{ color: 'var(--text-muted)' }}>{(pagination.page - 1) * pagination.size + index + 1}</td>
                  <td><strong>{cv.filename}</strong><div className="row-hint text-xs text-brand mt-1" style={{ opacity: 0.8 }}>Nhấn để xem chi tiết</div></td>
                  <td>{cv.user_id}</td>
                  <td><span className={'status-text ' + cv.status}>{cv.status}</span></td>
                  <td style={{ color: 'var(--text-muted)' }}>{new Date(cv.created_at).toLocaleString('vi-VN')}</td>
                  <td><button className="icon-btn danger" onClick={(event) => { event.stopPropagation(); remove(cv.id); }} title="Xóa"><Trash2 size={14} /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {!loading && cvsQuery.isSuccess && pagination.pages > 1 && (
          <div className="pagination-controls" style={{ padding: '20px' }}>
            <button className="btn btn-ghost btn-sm" onClick={() => setCurrentPage((page) => Math.max(1, page - 1))} disabled={currentPage <= 1}><ChevronLeft size={16} /> Trước</button>
            <span className="pagination-info text-muted text-xs">{currentPage} / {pagination.pages}</span>
            <button className="btn btn-ghost btn-sm" onClick={() => setCurrentPage((page) => Math.min(pagination.pages, page + 1))} disabled={currentPage >= pagination.pages}>Sau <ChevronRight size={16} /></button>
          </div>
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
  const queryClient = useQueryClient();
  const [currentPage, setCurrentPage] = useState(1);
  const [search, setSearch] = useState('');
  const currentUser = useAuthStore(state => state.user);
  const params = { page: currentPage, size: 20, search: search.trim() || undefined };
  const usersQuery = useQuery<AdminUserListResponse>({
    queryKey: ['admin', 'users', params],
    queryFn: () => adminApi.users(params),
  });
  const users = usersQuery.data?.items ?? [];
  const pagination = usersQuery.data ?? { total: 0, page: currentPage, size: 20, pages: 1, active_total: 0 };
  const loading = usersQuery.isPending;
  const loadError = usersQuery.isError;
  const load = () => { void queryClient.invalidateQueries({ queryKey: ['admin', 'users'] }); };
  const activeMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: number; isActive: boolean }) => adminApi.updateUserActive(id, isActive),
    onSuccess: async (_updated, variables) => {
      toast.success(variables.isActive ? 'Đã mở khóa tài khoản' : 'Đã khóa tài khoản');
      await queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
    },
    onError: (error: unknown) => {
      const detail = isAxiosError(error) ? error.response?.data?.detail : undefined;
      toast.error(typeof detail === 'string' ? detail : 'Không thể cập nhật tài khoản');
    },
  });
  const toggleActive = (user: User) => {
    if (!activeMutation.isPending) activeMutation.mutate({ id: user.id, isActive: !user.is_active });
  };

  return (
    <>
      <div className="admin-stats">
        <div className="admin-stat-card">
          <div className="admin-stat-icon"><Users size={20} /></div>
          <div><p>{search.trim() ? 'Người dùng phù hợp' : 'Tổng người dùng'}</p><strong>{loading || loadError ? '—' : pagination.total}</strong></div>
        </div>
        <div className="admin-stat-card">
          <div className="admin-stat-icon"><UserCheck size={20} /></div>
          <div><p>Đang hoạt động</p><strong>{loading || loadError ? '—' : pagination.active_total}</strong></div>
        </div>
      </div>
      <div className="admin-toolbar">
        <div className="admin-search">
          <Search size={16} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
          <input aria-label="Tìm người dùng" placeholder="Tìm theo tên hoặc email..." value={search} onChange={event => { setSearch(event.target.value); setCurrentPage(1); }} />
        </div>
        <button className="btn btn-ghost" onClick={load} title="Làm mới" disabled={usersQuery.isFetching}><RefreshCw size={16} /></button>
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
        ) : users.length === 0 ? (
          <div className="admin-empty"><Users size={40} /><h3>{search.trim() ? 'Không tìm thấy người dùng' : 'Chưa có người dùng'}</h3></div>
        ) : (
          <table className="admin-table">
            <thead><tr><th>STT</th><th>Người dùng</th><th>Quyền</th><th>Trạng thái</th><th>Ngày tạo</th><th>Thao tác</th></tr></thead>
            <tbody>
              {users.map((user, index) => (
                <tr key={user.id}>
                  <td style={{ color: 'var(--text-muted)' }}>{(pagination.page - 1) * pagination.size + index + 1}</td>
                  <td><strong>{user.full_name}</strong><div className="row-hint">{user.email}</div></td>
                  <td>{user.role === 'admin' ? 'Admin' : user.role === 'employer' ? 'Nhà tuyển dụng' : 'Người dùng'}</td>
                  <td><span className={`status-text ${user.is_active ? 'analyzed' : 'failed'}`}>{user.is_active ? 'Hoạt động' : 'Đã khóa'}</span></td>
                  <td style={{ color: 'var(--text-muted)' }}>{new Date(user.created_at).toLocaleDateString('vi-VN')}</td>
                  <td>
                    <button className={`btn ${user.is_active ? 'btn-danger' : 'btn-secondary'}`} onClick={() => toggleActive(user)} disabled={user.id === currentUser?.id || usersQuery.isFetching || activeMutation.isPending} title={user.id === currentUser?.id ? 'Không thể tự khóa tài khoản' : undefined}>
                      {user.is_active ? <UserX size={15} /> : <UserCheck size={15} />}{user.is_active ? 'Khóa' : 'Mở khóa'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Pagination Controls */}
        {!loading && !loadError && pagination.pages > 1 && (
          <div className="pagination-controls" style={{ padding: '20px' }}>
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => setCurrentPage(pagination.page - 1)}
              disabled={pagination.page <= 1 || usersQuery.isFetching}
            >
              <ChevronLeft size={16} /> Trước
            </button>
            <span className="pagination-info text-muted text-xs">
              Trang {pagination.page} / {pagination.pages} · {pagination.total} người dùng
            </span>
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => setCurrentPage(pagination.page + 1)}
              disabled={pagination.page >= pagination.pages || usersQuery.isFetching}
            >
              Sau <ChevronRight size={16} />
            </button>
          </div>
        )}
      </div>
    </>
  );
}

// Main AdminPage
// ------------------------------------------------------------------------------
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
