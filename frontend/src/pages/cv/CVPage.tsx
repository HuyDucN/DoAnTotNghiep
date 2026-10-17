import { useState, useCallback } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useDropzone } from 'react-dropzone';
import {
  UploadCloud, FileText, CheckCircle, XCircle,
  Loader2, Sparkles, RefreshCw, Eye, Trash2, AlertCircle,
} from 'lucide-react';
import { cvApi, getApiErrorMessage } from '../../services/api';
import type { CV } from '../../types';
import { syncCvAnalysisStarted, syncCvDeleted } from '../../services/cvCache';
import QueryLoadNotice from '../../components/QueryLoadNotice';
import toast from 'react-hot-toast';
import './CVPage.css';

// â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const STATUS_LABELS: Record<string, string> = {
  uploaded:   'Đã tải lên',
  processing: 'Đang phân tích',
  analyzed:   'Đã phân tích',
  failed:     'Phân tích lỗi',
};

function StatusIcon({ status }: { status: string }) {
  if (status === 'analyzed') return <CheckCircle size={16} />;
  if (status === 'failed')   return <XCircle size={16} />;
  if (status === 'processing' || status === 'uploaded')
    return <Loader2 size={16} className="animate-spin" />;
  return <AlertCircle size={16} />;
}

function formatSize(bytes?: number) {
  if (!bytes) return '—';
  return (bytes / 1024 / 1024).toFixed(2) + ' MB';
}

// â”€â”€ Main Component â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export default function CVPage() {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState<number | null>(null);

  const cvsQuery = useQuery<CV[]>({
    queryKey: ['cvs', 'mine'],
    queryFn: () => cvApi.list(),
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => cvApi.upload(file),
    onSuccess: async (cv: CV) => {
      toast.success('Đã tải CV lên! AI đang bắt đầu phân tích...');
      await syncCvAnalysisStarted(queryClient, cv);
    },
    onError: (err: unknown) => {
      toast.error(getApiErrorMessage(err, 'Không thể tải CV. Hãy thử lại.'));
    },
  });

  const retryMutation = useMutation({
    mutationFn: (id: number) => cvApi.reanalyze(id),
    onSuccess: async (cv: CV) => {
      toast.success('Đã bắt đầu phân tích lại.');
      await syncCvAnalysisStarted(queryClient, cv);
    },
    onError: (err: unknown) => {
      toast.error(getApiErrorMessage(err, 'Không thể phân tích lại.'));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => cvApi.delete(id),
    onSuccess: async (_, deletedId) => {
      toast.success('Đã xóa CV.');
      if (expanded === deletedId) setExpanded(null);
      await syncCvDeleted(queryClient, deletedId);
    },
    onError: (err: unknown) => {
      toast.error(getApiErrorMessage(err, 'Không thể xóa CV.'));
    },
  });

  const cvs = cvsQuery.data ?? [];
  const loading = cvsQuery.isPending;
  const uploading = uploadMutation.isPending;

  const onDrop = useCallback((files: File[]) => {
    const file = files[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      toast.error('File không được vượt quá 10MB.');
      return;
    }
    uploadMutation.mutate(file);
  }, [uploadMutation]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    maxSize: 10 * 1024 * 1024,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    onDropRejected: () => toast.error('Chỉ chấp nhận PDF hoặc DOCX, tối đa 10MB.'),
    disabled: uploading,
  });

  const handleRetry = (id: number) => {
    retryMutation.mutate(id);
  };

  const handleDelete = (cv: CV) => {
    if (!window.confirm('Xóa CV "' + cv.filename + '"? Hành động này không thể hoàn tác.')) return;
    deleteMutation.mutate(cv.id);
  };

  const handleViewFile = async (cv: CV) => {
    try {
      await cvApi.viewFile(cv.id, cv.filename);
    } catch {
      toast.error('Không thể mở file gốc. Hãy cho phép popup trên trình duyệt.');
    }
  };

  const retrying = retryMutation.isPending ? retryMutation.variables : null;
  const deleting = deleteMutation.isPending ? deleteMutation.variables : null;

  return (
    <main className="cv-page animate-fade-in">
      {/* Header */}
      <header className="cv-page-intro">
        <div>
          <p className="eyebrow">HỒ SƠ NGHỀ NGHIỆP</p>
          <h1>Phân tích CV bằng AI</h1>
          <p className="intro-copy">
            Tải CV lên để khám phá kỹ năng, kinh nghiệm và cơ hội phát triển phù hợp.
          </p>
        </div>
        <div className="intro-stat">
          <Sparkles size={17} /> Phân tích tự động
        </div>
      </header>

      <div className="cv-grid">
        {/* â”€â”€ Upload Section â”€â”€ */}
        <section className="card upload-section">
          <div className="panel-header">
            <div>
              <p className="section-kicker">BƯỚC 01</p>
              <h3>Tải CV của bạn</h3>
            </div>
            <span className="file-badge">PDF · DOCX · 10MB</span>
          </div>

          <div
            {...getRootProps()}
            className={`dropzone${isDragActive ? ' active' : ''}${uploading ? ' disabled' : ''}`}
            aria-label="Khu vực tải CV"
          >
            <input {...getInputProps()} />
            <div className="upload-icon-wrap">
              <UploadCloud size={30} />
            </div>
            <h4>{isDragActive ? 'Thả file vào đây' : 'Kéo thả CV hoặc chọn từ thiết bị'}</h4>
            <p className="text-muted">Hỗ trợ PDF và DOCX. File của bạn được bảo mật.</p>
            <span className="upload-cta">Chọn file từ máy tính</span>

            {uploading && (
              <div className="upload-overlay">
                <Loader2 className="animate-spin" size={30} />
                <span>Đang tải CV lên...</span>
              </div>
            )}
          </div>

          <div className="ai-notice">
            <div className="ai-notice-icon"><Sparkles size={17} /></div>
            <p>
              <strong>AI sẽ làm gì?</strong><br />
              Tự động trích xuất kỹ năng, kinh nghiệm và gợi ý khoảng cách năng lực.
              {!import.meta.env.VITE_AI_ENABLED && (
                <span className="ai-offline-note"> (AI đang tạm offline — dữ liệu sẽ trống)</span>
              )}
            </p>
          </div>
        </section>

        {/* â”€â”€ CV List Section â”€â”€ */}
        <section className="card list-section">
          <div className="panel-header">
            <div>
              <p className="section-kicker">BƯỚC 02</p>
              <h3>Kết quả phân tích</h3>
            </div>
            <span className="count-badge">{cvsQuery.data !== undefined ? `${cvs.length} hồ sơ` : '—'}</span>
          </div>

          <QueryLoadNotice query={cvsQuery} label="danh sách CV" />

          {loading ? (
            <div className="empty-state">
              <Loader2 className="animate-spin" size={28} />
              <p>Đang tải hồ sơ...</p>
            </div>
          ) : cvsQuery.isSuccess && cvs.length === 0 ? (
            <div className="empty-state">
              <FileText size={42} />
              <h4>Chưa có hồ sơ nào</h4>
              <p className="text-muted">Tải lên CV đầu tiên để bắt đầu phân tích.</p>
            </div>
          ) : (
            <div className="cv-list">
              {cvs.map((cv) => (
                <article key={cv.id} className="cv-item">
                  {/* Icon */}
                  <div className="cv-icon">
                    <FileText size={22} />
                  </div>

                  {/* Info */}
                  <div className="cv-info">
                    {/* Header row */}
                    <div className="cv-header">
                      <h4 title={cv.filename}>{cv.filename}</h4>
                      <div
                        className={`cv-status ${cv.status}`}
                        role="status"
                        aria-live="polite"
                        aria-label={`Trạng thái ${cv.filename}: ${STATUS_LABELS[cv.status] || cv.status}`}
                      >
                        <StatusIcon status={cv.status} />
                        <span>{STATUS_LABELS[cv.status] || cv.status}</span>
                      </div>
                    </div>

                    {/* Meta row */}
                    <div className="cv-meta">
                      <span>CV #{cv.id}</span>
                      <span>•</span>
                      <span>{new Date(cv.created_at).toLocaleDateString('vi-VN')}</span>
                      <span>•</span>
                      <span>{formatSize(cv.file_size)}</span>
                      <button
                        type="button"
                        className="view-original"
                        onClick={() => handleViewFile(cv)}
                        aria-label={`Xem bản gốc ${cv.filename}`}
                      >
                        <Eye size={14} /> Xem bản gốc
                      </button>
                    </div>

                    {/* Skills preview (analyzed) */}
                    {cv.status === 'analyzed' && cv.ai_analysis?.skills && (
                      <div className="cv-skills-preview">
                        {cv.ai_analysis.skills.slice(0, 5).map((s, i) => (
                          <span key={i} className="skill-pill">{s.name}</span>
                        ))}
                        {cv.ai_analysis.skills.length > 5 && (
                          <span className="skill-pill extra">
                            +{cv.ai_analysis.skills.length - 5}
                          </span>
                        )}
                      </div>
                    )}

                    {/* AI summary toggle */}
                    {cv.status === 'analyzed' && cv.ai_analysis?.summary && (
                      <div className="cv-summary-area">
                        <button
                          type="button"
                          className="toggle-summary-btn"
                          onClick={() => setExpanded(expanded === cv.id ? null : cv.id)}
                          aria-expanded={expanded === cv.id}
                          aria-controls={`cv-summary-${cv.id}`}
                        >
                          {expanded === cv.id ? '▲ Ẩn tóm tắt' : '▼ Xem tóm tắt AI'}
                        </button>
                        {expanded === cv.id && (
                          <p id={`cv-summary-${cv.id}`} className="cv-summary-text">{cv.ai_analysis.summary}</p>
                        )}
                      </div>
                    )}

                    {/* Error row */}
                    {cv.status === 'failed' && (
                      <div className="cv-error">
                        <span>Phân tích chưa hoàn tất.</span>
                        <button
                          type="button"
                          className="retry-btn"
                          onClick={() => handleRetry(cv.id)}
                          disabled={retrying === cv.id}
                          aria-label={`Phân tích lại ${cv.filename}`}
                        >
                          <RefreshCw size={14} className={retrying === cv.id ? 'animate-spin' : ''} />
                          Thử lại
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Delete button */}
                  <button
                    type="button"
                    className="cv-delete-btn"
                    onClick={() => handleDelete(cv)}
                    disabled={deleting === cv.id}
                    aria-label={`Xóa CV ${cv.filename}`}
                    title={`Xóa CV ${cv.filename}`}
                  >
                    {deleting === cv.id
                      ? <Loader2 size={16} className="animate-spin" />
                      : <Trash2 size={16} />
                    }
                  </button>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

