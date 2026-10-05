# Kiến trúc hệ thống

## Thành phần
- **Frontend:** React 19, TypeScript, Vite; Axios gọi REST API; Zustand lưu trạng thái xác thực.
- **API:** FastAPI với các router auth, users, admin, CV, jobs và skills dưới `/api`.
- **Nghiệp vụ:** SQLAlchemy ORM; service trích xuất CV, phân tích AI và so khớp kỹ năng.
- **Lưu trữ:** MySQL qua PyMySQL; file CV nằm trong `UPLOAD_DIR` và được phục vụ qua endpoint có xác thực chủ sở hữu.
- **Tích hợp AI/OCR:** OpenAI-compatible chat completions; PyMuPDF và python-docx để trích xuất, Tesseract với ngôn ngữ mặc định `vie+eng` cho PDF scan.

## Luồng phân tích CV
1. Frontend gửi PDF/DOCX đến `POST /api/cv/upload`; API giới hạn dung lượng và kiểm tra chữ ký file.
2. File và bản ghi CV được lưu; background task trích xuất văn bản, chạy OCR khi PDF có ít hơn 80 ký tự có thể trích xuất.
3. Văn bản tối đa 12.000 ký tự, sau khi che email và số điện thoại, được gửi cho dịch vụ AI dưới dạng dữ liệu riêng; prompt yêu cầu bỏ qua chỉ dẫn nhúng trong CV.
4. Kết quả AI được kiểm tra bằng Pydantic rồi lưu vào CV và bảng liên kết kỹ năng; lỗi phân tích chuyển CV sang `failed`.

## Luồng so khớp
1. API xác nhận CV thuộc người gọi, đã phân tích và job còn hoạt động.
2. `skill_matcher` so tên kỹ năng đã chuẩn hóa; required skill cần đạt mức tối thiểu theo job level, preferred skill chỉ cần tồn tại.
3. Điểm tính theo trọng số 1.0 cho required, 0.3 cho preferred; kết quả gồm matched, missing, weak skills và AI recommendation.
4. Kết quả được upsert theo bộ `(user_id, cv_id, job_id)`; unique constraint ở model bảo vệ dữ liệu khỏi ghi trùng đồng thời.

## Mô hình dữ liệu
- `users` có một `profile`, nhiều `cvs` và `skill_gaps`.
- `cvs` lưu file path, trạng thái, raw text và JSON phân tích; `cv_skills` nối CV với `skills` và ghi proficiency/years.
- `jobs` nối với `skills` qua `job_skills`, gồm cờ required và importance.
- `skill_gaps` nối user, CV và job, lưu điểm, nhóm kỹ năng và gợi ý.
- `skills.normalized_name` và `skills.name` là duy nhất. `skill_gaps` có unique constraint cho một bộ user-CV-job.

## Xác thực và cấu hình
- JWT xác định user; dependency `get_current_user` và `get_current_admin` kiểm soát quyền ở API.
- Rate limit dùng địa chỉ IP kết nối trực tiếp và route template, không tin `X-Forwarded-For`; trạng thái hiện nằm trong bộ nhớ tiến trình.
- Cấu hình đọc từ `.env`: DB, JWT, môi trường/DEBUG, AI provider/model, CORS, upload và Tesseract.
- Khi `ENVIRONMENT` là production, ứng dụng từ chối secret quá ngắn, thiếu DB password hoặc bật DEBUG.
- `Base.metadata.create_all` chỉ chạy trong development. Thư mục `backend/alembic` hiện chưa có cấu hình/revision; migration cho DB đang chạy được quản lý riêng và phải kiểm tra dữ liệu trước khi thêm constraint.

## Công nghệ
- Python, FastAPI, Pydantic, SQLAlchemy, Alembic dependency, MySQL/PyMySQL.
- React, TypeScript, Vite, Axios, Zustand.
- PyMuPDF, python-docx, Pillow, pytesseract và Tesseract OCR.
- OpenAI Python SDK gọi endpoint OpenAI-compatible; URL nhà cung cấp do cấu hình môi trường quyết định.
