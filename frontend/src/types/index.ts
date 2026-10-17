// ── Kiểu phân trang chung (dùng cho Jobs, CVs, Users) ────────────────────────
export interface PaginatedResponse<T> {
  items: T[];
  total: number;   // Tổng số bản ghi
  page: number;    // Trang hiện tại
  size: number;    // Số bản ghi mỗi trang
  pages: number;   // Tổng số trang
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'user' | 'admin' | 'employer';
  is_active: boolean;
  created_at: string;
}

export interface AdminUserListResponse extends PaginatedResponse<User> {
  active_total: number;
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

export interface AccountResponse {
  user: User;
  profile: Profile | null;
}

export interface AccountUpdate {
  full_name?: string;
  phone?: string | null;
  location?: string | null;
  job_title?: string | null;
  bio?: string | null;
  linkedin_url?: string | null;
  github_url?: string | null;
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

export interface CVStatus {
  id: number;
  status: 'uploaded' | 'processing' | 'analyzed' | 'failed';
  updated_at?: string;
}

export interface CVSkillItem {
  id: number;
  skill_id: number;
  skill_name: string;
  proficiency_level: 'beginner' | 'intermediate' | 'advanced' | 'expert';
  years_experience: number;
  source: 'ai_extracted' | 'manual' | string;
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

export interface AdminJobListResponse extends PaginatedResponse<Job> {
  active_total: number;
  category_count: number;
}

export interface JobSkill {
  skill_id: number;
  skill_name: string;
  is_required: boolean;
  importance: 'high' | 'medium' | 'low';
}

export interface SkillGroupScore {
  importance: 'high' | 'medium' | 'low';
  matched_weight: number;
  total_weight: number;
  score: number;
}

export type CvMatchStatus = 'current' | 'changed' | 'processing' | 'failed' | 'unknown';

export interface SkillGapResult {
  id: number;
  cv_id: number;
  cv_filename: string;
  cv_match_status: CvMatchStatus;
  match_score: number;
  matched_skills: MatchedSkill[];
  missing_skills: MissingSkill[];
  weak_skills: WeakSkill[];
  skill_group_scores?: SkillGroupScore[] | null;
  ai_recommendation?: string;
  job: Job;
  created_at: string;
  matched_at?: string | null;
  job_snapshot_available?: boolean;
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

export interface Skill {
  id: number;
  name: string;
  normalized_name: string;
  category: string;
  description?: string;
}

export interface JobSkillInput {
  skill_name: string;
  is_required: boolean;
  importance: 'high' | 'medium' | 'low';
}

export interface JobDescriptionParseResult {
  title: string;
  company?: string | null;
  location?: string | null;
  job_type: 'full_time' | 'part_time' | 'internship' | 'freelance';
  level: 'intern' | 'fresher' | 'junior' | 'mid' | 'senior' | 'lead';
  category: 'backend' | 'frontend' | 'fullstack' | 'data' | 'ai_ml' | 'devops' | 'mobile' | 'qa' | 'other';
  salary_min?: number | null;
  salary_max?: number | null;
  required_skills: JobSkillInput[];
  preferred_skills: JobSkillInput[];
}
