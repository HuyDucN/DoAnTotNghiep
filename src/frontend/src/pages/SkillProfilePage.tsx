import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../store/authStore';
import { authApi, cvApi } from '../services/api';
import type { Profile, CV, CVAnalysis } from '../types';
import { User, MapPin, Briefcase, Mail, Phone, GitBranch, Globe, Award, Code, BookOpen } from 'lucide-react';
import toast from 'react-hot-toast';
import './SkillProfile.css';

export default function SkillProfilePage() {
  const user = useAuthStore((s) => s.user);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [latestCv, setLatestCv] = useState<CV | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [profileData, cvsData] = await Promise.all([
          authApi.getProfile(),
          cvApi.list()
        ]);
        setProfile(profileData);
        
        // Find latest analyzed CV
        const analyzedCvs = cvsData.filter((cv: CV) => cv.status === 'analyzed' && cv.ai_analysis);
        if (analyzedCvs.length > 0) {
          setLatestCv(analyzedCvs[0]);
        }
      } catch (error) {
        toast.error('Lỗi tải dữ liệu profile');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return <div className="flex justify-center mt-10"><span className="spinner"></span></div>;
  }

  const analysis: CVAnalysis | undefined = latestCv?.ai_analysis;

  return (
    <div className="skill-profile-page animate-fade-in">
      <div className="profile-header card">
        <div className="profile-avatar bg-brand">
          {user?.full_name.charAt(0).toUpperCase()}
        </div>
        <div className="profile-info-main">
          <h2>{analysis?.full_name || user?.full_name}</h2>
          <p className="profile-headline">{analysis?.summary || profile?.job_title || 'Chưa có chức danh'}</p>
          <div className="profile-meta flex items-center gap-4 text-muted mt-2">
            <span className="flex items-center gap-1"><Mail size={14}/> {user?.email}</span>
            {(analysis?.phone || profile?.phone) && <span className="flex items-center gap-1"><Phone size={14}/> {analysis?.phone || profile?.phone}</span>}
            {(analysis?.location || profile?.location) && <span className="flex items-center gap-1"><MapPin size={14}/> {analysis?.location || profile?.location}</span>}
          </div>
        </div>
        <div className="profile-stats">
          <div className="stat-box">
             <strong>{analysis?.total_experience_years || 0}</strong>
             <span>Năm kinh nghiệm</span>
          </div>
          <div className="stat-box">
             <strong>{analysis?.skills.length || 0}</strong>
             <span>Kỹ năng AI tìm thấy</span>
          </div>
        </div>
      </div>

      <div className="profile-grid mt-6">
        <div className="profile-column left">
          <div className="card">
            <div className="panel-header mb-4">
              <h3><Code size={18} className="inline mr-2" /> Kỹ năng</h3>
            </div>
            {!analysis?.skills ? (
              <p className="text-muted text-sm">Chưa có dữ liệu kỹ năng. Hãy phân tích CV.</p>
            ) : (
              <div className="skills-categorized">
                {/* Group skills by category */}
                {['programming_language', 'framework', 'database', 'cloud', 'devops', 'ai_ml', 'soft_skill', 'tool', 'other'].map(cat => {
                  const skillsInCat = analysis.skills.filter(s => s.category === cat);
                  if (skillsInCat.length === 0) return null;
                  
                  const catLabels: Record<string, string> = {
                    programming_language: 'Ngôn ngữ', framework: 'Framework', database: 'Database', cloud: 'Cloud', devops: 'DevOps', ai_ml: 'AI / Machine Learning', soft_skill: 'Kỹ năng mềm', tool: 'Công cụ', other: 'Khác'
                  };

                  return (
                    <div key={cat} className="skill-category mb-4">
                      <h4 className="text-sm font-semibold mb-2 text-secondary">{catLabels[cat]}</h4>
                      <div className="flex flex-wrap gap-2">
                        {skillsInCat.map(skill => (
                          <div key={skill.name} className={`skill-badge level-${skill.proficiency_level}`}>
                            {skill.name}
                            <span className="skill-level">{skill.proficiency_level}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        <div className="profile-column right">
          <div className="card mb-6">
            <div className="panel-header mb-4">
              <h3><Briefcase size={18} className="inline mr-2" /> Kinh nghiệm</h3>
            </div>
            {!analysis?.experience || analysis.experience.length === 0 ? (
               <p className="text-muted text-sm">Không có dữ liệu kinh nghiệm.</p>
            ) : (
              <div className="timeline">
                {analysis.experience.map((exp, i) => (
                  <div key={i} className="timeline-item">
                    <div className="timeline-dot"></div>
                    <div className="timeline-content">
                      <h4>{exp.position} tại <strong>{exp.company}</strong></h4>
                      <div className="timeline-date">{exp.start_date} - {exp.end_date}</div>
                      <p className="timeline-desc text-sm mt-1">{exp.description}</p>
                      {exp.skills_used && exp.skills_used.length > 0 && (
                        <div className="mt-2 flex gap-1 flex-wrap">
                          {exp.skills_used.map(s => <span key={s} className="mini-skill">{s}</span>)}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card">
            <div className="panel-header mb-4">
              <h3><BookOpen size={18} className="inline mr-2" /> Học vấn & Chứng chỉ</h3>
            </div>
            <div className="education-list mb-4">
               {!analysis?.education || analysis.education.length === 0 ? null : (
                 analysis.education.map((edu, i) => (
                   <div key={i} className="edu-item mb-3">
                     <h4>{edu.degree} - {edu.field_of_study}</h4>
                     <p className="text-sm text-secondary">{edu.institution} ({edu.start_year} - {edu.end_year})</p>
                   </div>
                 ))
               )}
            </div>
            
            <div className="cert-list">
               {!analysis?.certificates || analysis.certificates.length === 0 ? null : (
                 analysis.certificates.map((cert, i) => (
                   <div key={i} className="cert-item flex items-center gap-2 mb-2">
                     <Award size={16} className="text-warning" />
                     <span className="text-sm">{cert.name} ({cert.year})</span>
                   </div>
                 ))
               )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
