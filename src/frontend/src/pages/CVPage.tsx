import React, { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, FileText, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { cvApi } from '../services/api';
import type { CV } from '../types';
import toast from 'react-hot-toast';
import './CVPage.css';

export default function CVPage() {
  const [cvs, setCvs] = useState<CV[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  const fetchCVs = async () => {
    try {
      const data = await cvApi.list();
      setCvs(data);
    } catch (error) {
      toast.error('Lỗi khi tải danh sách CV');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCVs();
    // Poll for status updates if any CV is processing
    const interval = setInterval(() => {
      if (cvs.some((cv) => cv.status === 'processing' || cv.status === 'uploaded')) {
        fetchCVs();
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [cvs]);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
      return toast.error('File không được vượt quá 10MB');
    }

    setUploading(true);
    try {
      await cvApi.upload(file);
      toast.success('Upload thành công! Đang phân tích bằng AI...');
      fetchCVs();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Lỗi khi upload CV');
    } finally {
      setUploading(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc']
    },
    multiple: false
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'analyzed': return <CheckCircle className="text-success" size={20} />;
      case 'failed': return <XCircle className="text-danger" size={20} />;
      case 'processing': return <Loader2 className="text-info animate-spin" size={20} />;
      default: return <Loader2 className="text-muted animate-spin" size={20} />;
    }
  };

  return (
    <div className="cv-page animate-fade-in">
      <div className="cv-grid">
        <div className="card upload-section">
          <div className="panel-header">
            <h3>Tải lên CV mới</h3>
            <span className="badge badge-neutral">PDF / DOCX</span>
          </div>

          <div
            {...getRootProps()}
            className={`dropzone ${isDragActive ? 'active' : ''} ${uploading ? 'disabled' : ''}`}
          >
            <input {...getInputProps()} />
            <UploadCloud size={48} className="dropzone-icon" />
            <h4>{isDragActive ? 'Thả file vào đây...' : 'Kéo thả hoặc click để chọn file'}</h4>
            <p className="text-muted">Hỗ trợ định dạng PDF, DOCX (Tối đa 10MB)</p>
            {uploading && <div className="upload-overlay"><Loader2 className="animate-spin" size={32} /></div>}
          </div>

          <div className="ai-notice">
            <div className="ai-notice-icon">✨</div>
            <p>Hệ thống sử dụng <strong>Gemini 1.5 Pro</strong> để tự động trích xuất kỹ năng, kinh nghiệm và tính toán khoảng cách năng lực của bạn.</p>
          </div>
        </div>

        <div className="card list-section">
          <div className="panel-header">
            <h3>Hồ sơ đã phân tích</h3>
            <span className="badge badge-primary">{cvs.length} hồ sơ</span>
          </div>

          {loading ? (
            <div className="flex justify-center p-8"><Loader2 className="animate-spin text-brand" size={32} /></div>
          ) : cvs.length === 0 ? (
            <div className="empty-state">
              <FileText size={48} className="text-muted mb-4" />
              <h4>Chưa có hồ sơ nào</h4>
              <p className="text-muted">Hãy tải lên CV đầu tiên của bạn để bắt đầu phân tích.</p>
            </div>
          ) : (
            <div className="cv-list">
              {cvs.map((cv) => (
                <div key={cv.id} className="cv-item">
                  <div className="cv-icon">
                    <FileText size={24} className="text-brand" />
                  </div>
                  <div className="cv-info">
                    <div className="cv-header">
                      <h4>{cv.filename}</h4>
                      <div className="cv-status" title={cv.status}>
                        {getStatusIcon(cv.status)}
                        <span className={`status-text ${cv.status}`}>{cv.status}</span>
                      </div>
                    </div>
                    <div className="cv-meta">
                      <span>{new Date(cv.created_at).toLocaleDateString('vi-VN')}</span>
                      <span>•</span>
                      <span>{(cv.file_size ? cv.file_size / 1024 / 1024 : 0).toFixed(2)} MB</span>
                    </div>

                    {cv.status === 'analyzed' && cv.ai_analysis?.skills && (
                      <div className="cv-skills-preview">
                        {cv.ai_analysis.skills.slice(0, 4).map((skill, idx) => (
                          <span key={idx} className="skill-pill">{skill.name}</span>
                        ))}
                        {cv.ai_analysis.skills.length > 4 && (
                          <span className="skill-pill extra">+{cv.ai_analysis.skills.length - 4}</span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
