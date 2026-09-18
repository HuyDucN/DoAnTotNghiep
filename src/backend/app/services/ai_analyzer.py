"""
AI Analyzer Service — Google Gemini 1.5 Flash
Phân tích CV text → structured JSON với skills, education, experience, projects
"""
import json
import re
from typing import Optional
from app.core.config import settings

CV_ANALYSIS_PROMPT = """
Bạn là chuyên gia phân tích CV. Hãy phân tích CV sau và trả về JSON có cấu trúc chính xác như yêu cầu.

=== CV TEXT ===
{cv_text}
=== END CV ===

Trả về JSON với cấu trúc sau (KHÔNG thêm bất kỳ text nào bên ngoài JSON):
{{
  "full_name": "Tên đầy đủ",
  "email": "email@example.com",
  "phone": "số điện thoại",
  "location": "địa điểm",
  "summary": "Tóm tắt nghề nghiệp ngắn gọn",
  "total_experience_years": 0,
  "skills": [
    {{
      "name": "Python",
      "category": "programming_language",
      "proficiency_level": "advanced",
      "years_experience": 2
    }}
  ],
  "education": [
    {{
      "institution": "Tên trường",
      "degree": "Bằng cấp",
      "field_of_study": "Chuyên ngành",
      "start_year": 2019,
      "end_year": 2023,
      "gpa": 3.5
    }}
  ],
  "experience": [
    {{
      "company": "Tên công ty",
      "position": "Chức vụ",
      "start_date": "MM/YYYY",
      "end_date": "MM/YYYY hoặc Present",
      "description": "Mô tả công việc",
      "skills_used": ["Python", "SQL"]
    }}
  ],
  "projects": [
    {{
      "name": "Tên dự án",
      "description": "Mô tả dự án",
      "technologies": ["React", "Node.js"],
      "url": "link nếu có"
    }}
  ],
  "certificates": [
    {{
      "name": "Tên chứng chỉ",
      "issuer": "Tổ chức cấp",
      "year": 2022
    }}
  ]
}}

Quy tắc category cho skills:
- programming_language: Python, Java, JavaScript, C++, Go, Rust...
- framework: React, Django, FastAPI, Spring, Vue, Angular...
- database: MySQL, PostgreSQL, MongoDB, Redis...
- cloud: AWS, Azure, GCP, Vercel, Docker, Kubernetes...
- devops: CI/CD, Git, GitHub Actions, Jenkins, Linux...
- ai_ml: Machine Learning, Deep Learning, NLP, TensorFlow, PyTorch, Scikit-learn...
- soft_skill: Teamwork, Communication, Leadership, Problem Solving...
- tool: Figma, Postman, Jira, VS Code...
- other: Mặc định nếu không xác định được

proficiency_level: beginner | intermediate | advanced | expert
"""

RECOMMENDATION_PROMPT = """
Bạn là Career Advisor. Dựa trên thông tin sau, hãy đưa ra lời khuyên học tập ngắn gọn, thực tế (3-5 điểm).

Vị trí ứng tuyển: {job_title}
Kỹ năng còn thiếu: {missing_skills}
Thông tin ứng viên: {summary}

Trả về danh sách các lời khuyên ưu tiên theo định dạng:
1. [Kỹ năng] — Lý do cần học và cách học nhanh nhất
2. ...

Ngắn gọn, thực tế, bằng tiếng Việt.
"""


def _get_gemini_model():
    """Initialize Gemini model."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        return genai.GenerativeModel("gemini-2.0-flash")
    except ImportError:
        raise RuntimeError("google-generativeai chưa được cài đặt")


def analyze_cv_with_ai(cv_text: str) -> Optional[dict]:
    """
    Gửi CV text lên Gemini → parse JSON kết quả.
    Returns: dict with structured CV data, or None if failed.
    """
    if not settings.GEMINI_API_KEY:
        # Fallback: return mock data for development
        return _mock_cv_analysis()

    import time
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            model = _get_gemini_model()
            prompt = CV_ANALYSIS_PROMPT.format(cv_text=cv_text[:8000])  # Limit text length
            response = model.generate_content(prompt)
            raw = response.text.strip()

            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
            if json_match:
                raw = json_match.group(1)
            elif raw.startswith("{"):
                pass  # Already raw JSON
            else:
                # Find first { to last }
                start = raw.find("{")
                end = raw.rfind("}") + 1
                if start != -1 and end > start:
                    raw = raw[start:end]

            return json.loads(raw)
        except Exception as e:
            print(f"[AI Analyzer] Error (Attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s...
            else:
                print(f"[AI Analyzer] Failed after {max_retries} attempts.")
                return None


def generate_recommendation(
    cv_analysis: Optional[dict],
    missing_skills: list,
    job_title: str,
) -> str:
    """Generate AI career recommendation text."""
    if not settings.GEMINI_API_KEY or not missing_skills:
        return _mock_recommendation(missing_skills, job_title)

    try:
        model = _get_gemini_model()
        summary = cv_analysis.get("summary", "") if cv_analysis else ""
        skills_text = ", ".join([s.get("skill_name", "") for s in missing_skills[:10]])

        prompt = RECOMMENDATION_PROMPT.format(
            job_title=job_title,
            missing_skills=skills_text,
            summary=summary,
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"[Recommendation] Error: {e}")
        return _mock_recommendation(missing_skills, job_title)


def _mock_cv_analysis() -> dict:
    """Mock data for development without API key."""
    return {
        "full_name": "Nguyễn Văn A",
        "email": "nguyenvana@example.com",
        "phone": "0901234567",
        "location": "Hà Nội",
        "summary": "Sinh viên CNTT năm 4, có kinh nghiệm Python và Web Development",
        "total_experience_years": 1,
        "skills": [
            {"name": "Python", "category": "programming_language", "proficiency_level": "intermediate", "years_experience": 2},
            {"name": "React", "category": "framework", "proficiency_level": "beginner", "years_experience": 0.5},
            {"name": "SQL", "category": "database", "proficiency_level": "intermediate", "years_experience": 1},
            {"name": "Git", "category": "devops", "proficiency_level": "intermediate", "years_experience": 2},
        ],
        "education": [{"institution": "Đại học Bách Khoa", "degree": "Kỹ sư", "field_of_study": "Công nghệ thông tin", "start_year": 2020, "end_year": 2024}],
        "experience": [],
        "projects": [{"name": "E-commerce Website", "description": "Website bán hàng bằng Django", "technologies": ["Python", "Django", "MySQL"]}],
        "certificates": [],
    }


def _mock_recommendation(missing_skills: list, job_title: str) -> str:
    skills = [s.get("skill_name", "Kỹ năng") for s in missing_skills[:3]]
    recs = []
    for i, skill in enumerate(skills, 1):
        recs.append(f"{i}. {skill} — Học qua khóa học online (Udemy/Coursera) và thực hành qua dự án cá nhân.")
    return "\n".join(recs) if recs else f"Bạn đang thiếu một số kỹ năng cần thiết cho vị trí {job_title}. Hãy tập trung học các công nghệ cốt lõi."
