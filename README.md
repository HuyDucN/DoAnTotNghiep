# AI CV Skill Gap

Hệ thống phân tích khoảng cách kỹ năng (Skill Gap) trên CV bằng AI — so sánh kỹ năng ứng viên với yêu cầu công việc, tính match score và đưa ra lời khuyên học tập.

## Cấu trúc thư mục

```
DoAnTotNghiep/
├── backend/                    # FastAPI (Python)
│   ├── app/
│   │   ├── api/                # Route handlers: auth, cv, jobs, skills, users, admin
│   │   ├── core/               # Config, database, security (JWT)
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic schemas
│   │   └── services/           # AI analyzer, CV parser, skill matcher
│   ├── uploads/                # CV files (PDF/DOCX)
│   ├── .env                    # Biến môi trường (tạo từ .env.example)
│   └── requirements.txt
│
├── frontend/                   # React + Vite + TypeScript
│   └── src/
│       ├── components/
│       │   └── layout/         # AppLayout, Sidebar, Topbar
│       ├── pages/
│       │   ├── auth/           # Login, Register, ForgotPassword, ResetPassword
│       │   ├── dashboard/      # DashboardPage
│       │   ├── cv/             # CVPage (upload & quản lý CV)
│       │   ├── jobs/           # JobsPage (tìm việc & match)
│       │   ├── profile/        # SkillProfilePage
│       │   ├── reports/        # ReportsPage (lịch sử phân tích)
│       │   ├── settings/       # SettingsPage
│       │   └── admin/          # AdminPage (quản trị)
│       ├── services/           # API client (axios)
│       ├── store/              # Zustand auth store
│       ├── types/              # TypeScript interfaces
│       └── styles/             # Global CSS
│
├── docs/
│   ├── architecture/
│   └── requirements/
│
├── scripts/                    # PowerShell scripts tiện ích
│   ├── setup.ps1               # Cài đặt toàn bộ dependencies
│   ├── start_backend.ps1       # Khởi động Backend
│   └── start_frontend.ps1      # Khởi động Frontend
│
└── README.md
```

## Hướng dẫn cài đặt lần đầu

```powershell
# Clone project và chạy setup
cd d:\DoAnTotNghiep
.\scripts\setup.ps1
```

Sau đó chỉnh sửa `backend\.env` với thông tin thực tế của bạn (DB, Gemini API key).

## Chạy dự án (Development)

Mở **2 terminal** và chạy song song:

**Terminal 1 — Backend:**
```powershell
.\scripts\start_backend.ps1
```
→ API chạy tại: http://localhost:8000  
→ Swagger UI: http://localhost:8000/docs

**Terminal 2 — Frontend:**
```powershell
.\scripts\start_frontend.ps1
```
→ App chạy tại: http://localhost:5173

## Chạy thủ công (nếu cần)

```powershell
# Backend
cd d:\DoAnTotNghiep\backend
python -m uvicorn app.main:app --reload --port 8000

# Frontend
cd d:\DoAnTotNghiep\frontend
npm run dev
```

## Stack công nghệ

| Thành phần | Công nghệ |
|------------|-----------|
| Backend    | FastAPI, SQLAlchemy, MySQL, Alembic |
| AI         | Google Gemini 1.5 Flash |
| Frontend   | React 18, Vite, TypeScript, Zustand, Axios |
| Auth       | JWT (python-jose), bcrypt |
| CV Parsing | PyMuPDF, python-docx, Tesseract OCR |

> *Lưu ý: Bạn có thể đăng nhập bằng tính năng "Tài khoản demo" trên giao diện để trải nghiệm nhanh các tính năng AI giả lập.*
