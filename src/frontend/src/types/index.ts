export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'user' | 'admin';
  is_active: boolean;
  created_at: string;
}

export interface Profile {
  id: number;
  user_id: number;
  phone?: string;
  location?: string;
  job_title?: string;
  bio?: string;
  avatar_url?: string;
  linkedin_url?: string;
  github_url?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface CV {
  id: number;
  user_id: number;
  filename: string;
  file_size?: number;
  status: 'uploaded' | 'processing' | 'analyzed' | 'failed';
  ai_analysis?: CVAnalysis;
  created_at: string;
}

export interface CVAnalysis {
  full_name?: string;
  email?: string;
  phone?: string;
  location?: string;
  summary?: string;
  total_experience_years?: number;
  skills: SkillItem[];
  education: EducationItem[];
  experience: ExperienceItem[];
  projects: ProjectItem[];
  certificates: CertificateItem[];
}

export interface SkillItem {
  name: string;
  category: string;
  proficiency_level: 'beginner' | 'intermediate' | 'advanced' | 'expert';
  years_experience: number;
}

export interface EducationItem {
  institution: string;
  degree: string;
  field_of_study: string;
  start_year?: number;
  end_year?: number;
  gpa?: number;
}

export interface ExperienceItem {
  company: string;
  position: string;
  start_date?: string;
  end_date?: string;
  description?: string;
  skills_used: string[];
}

export interface ProjectItem {
  name: string;
  description?: string;
  technologies: string[];
  url?: string;
}

export interface CertificateItem {
  name: string;
  issuer?: string;
  year?: number;
}

export interface Job {
  id: number;
  title: string;
  company?: string;
  location?: string;
  job_type: string;
  level: string;
  category: string;
  description?: string;
  salary_min?: number;
  salary_max?: number;
  is_active: boolean;
  job_skills: JobSkill[];
  created_at: string;
}

export interface JobSkill {
  skill_id: number;
  skill_name: string;
  is_required: boolean;
  importance: 'high' | 'medium' | 'low';
}

export interface SkillGapResult {
  id: number;
  match_score: number;
  matched_skills: MatchedSkill[];
  missing_skills: MissingSkill[];
  weak_skills: WeakSkill[];
  ai_recommendation?: string;
  job: Job;
  created_at: string;
}

export interface MatchedSkill {
  skill_id: number;
  skill_name: string;
  is_required: boolean;
  importance: string;
  cv_level: string;
  years_experience: number;
}

export interface MissingSkill {
  skill_id: number;
  skill_name: string;
  is_required: boolean;
  importance: string;
  priority: 'high' | 'medium' | 'low';
}

export interface WeakSkill {
  skill_id: number;
  skill_name: string;
  is_required: boolean;
  importance: string;
  current_level: string;
  needed_level: string;
  priority: 'high' | 'medium' | 'low';
}
