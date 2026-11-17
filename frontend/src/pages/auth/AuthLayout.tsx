import type { ReactNode } from 'react';
import { ArrowUpRight, Check, FileText, ScanLine, Sparkles, Target } from 'lucide-react';
import './AuthPage.css';

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="auth-page">
      <aside className="auth-story" aria-label="Giới thiệu CV Skill Gap">
        <div className="auth-story-brand"><span><Sparkles size={23} aria-hidden="true" /></span><strong>CV Skill Gap<span>.</span></strong></div>
        <div className="auth-story-content">
          <span className="auth-story-kicker"><span /> KHỞI ĐẦU CHO BƯỚC TIẾN MỚI</span>
          <h2>Một hồ sơ tốt.<br />Nhiều cánh cửa <em>mới.</em></h2>
          <p>Hiểu điều bạn giỏi, biết điều cần học.<br />Để mỗi bước trên hành trình sự nghiệp<br className="auth-story-break" /> đều có hướng đi rõ ràng.</p>
          <div className="auth-story-visual" aria-hidden="true">
            <div className="auth-preview-document">
              <span className="auth-preview-icon"><FileText size={26} strokeWidth={1.5} /></span>
              <span className="auth-preview-title">CV của bạn</span>
              <span className="auth-preview-line" /><span className="auth-preview-line short" />
              <span className="auth-preview-separator" />
              <span className="auth-preview-row"><Check size={12} /><i /></span>
              <span className="auth-preview-row"><Check size={12} /><i /></span>
              <span className="auth-preview-row"><Check size={12} /><i /></span>
              <span className="auth-preview-tags"><i /><i /><i /></span>
            </div>
            <div className="auth-preview-insight"><span><ScanLine size={18} /></span><div><strong>Khám phá thế mạnh</strong><small>Từ những kỹ năng của bạn</small></div><Sparkles size={13} /></div>
            <div className="auth-preview-opportunity"><span><Target size={18} /></span><div><strong>Kết nối cơ hội</strong><small>Đúng năng lực, đúng hướng đi</small></div><ArrowUpRight size={15} /></div>
            <span className="auth-visual-orbit" /><span className="auth-visual-dot dot-first" /><span className="auth-visual-dot dot-second" />
          </div>
          <div className="auth-story-features"><span><Check size={12} aria-hidden="true" />Phân tích CV</span><span><Check size={12} aria-hidden="true" />So khớp kỹ năng</span><span><Check size={12} aria-hidden="true" />Gợi ý phát triển</span></div>
        </div>
        <p className="auth-story-footer">HIỂU NĂNG LỰC. CHỦ ĐỘNG TƯƠNG LAI.</p>
      </aside>
      <main className="auth-form-panel">
        <div className="auth-card">{children}</div>
        <p className="auth-page-footer">Hành trình mới, bắt đầu từ chính bạn.</p>
      </main>
    </div>
  );
}