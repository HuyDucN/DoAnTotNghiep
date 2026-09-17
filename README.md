# AI CV Skill Gap

Dự án nghiên cứu và xây dựng hệ thống phân tích khoảng cách kỹ năng trên CV bằng AI.

## Cấu trúc thư mục

- `docs/requirements/` — tài liệu yêu cầu, mục tiêu, phạm vi dự án
- `docs/architecture/` — sơ đồ kiến trúc, thiết kế hệ thống
- `src/backend/` — API backend bằng FastAPI (Python)
- `src/frontend/` — Giao diện web bằng React + Vite (TypeScript)

## Hướng dẫn chạy dự án (Local Development)

Dự án gồm 2 phần độc lập cần được chạy song song: **Backend** và **Frontend**. Bạn cần mở 2 terminal (cửa sổ dòng lệnh) khác nhau.

### 1. Chạy Backend (FastAPI)

Mở terminal 1, di chuyển vào thư mục backend và chạy server:

```powershell
cd d:\DoAnTotNghiep\src\backend
# (Tùy chọn) Cài đặt thư viện nếu chưa cài: pip install -r requirements.txt

# Chạy server FastAPI
python -m uvicorn app.main:app --reload --port 8000
```
Sau khi chạy thành công, Backend sẽ hoạt động tại:
- API Docs (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Chạy Frontend (React + Vite)

Mở terminal 2, di chuyển vào thư mục frontend và khởi động Vite:

```powershell
cd d:\DoAnTotNghiep\src\frontend
# (Tùy chọn) Cài đặt dependencies nếu chưa cài: npm install

# Chạy development server
npm run dev
```
Sau khi chạy thành công, Frontend sẽ hoạt động tại:
- Giao diện Web: [http://localhost:5173](http://localhost:5173)

---
*Lưu ý: Bạn có thể đăng nhập bằng tính năng "Tài khoản demo" trên giao diện để trải nghiệm nhanh các tính năng AI giả lập.*
