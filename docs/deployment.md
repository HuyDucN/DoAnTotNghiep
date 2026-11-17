# Triển khai (Docker + VPS)

## 1. Chuẩn bị trên VPS (một lần)

1. Cài Docker + Docker Compose plugin.
2. Clone repo, checkout nhánh `main`.
3. Tạo file `.env` cạnh `docker-compose.yml`:
   ```bash
   cp .env.deploy.example .env
   nano .env   # điền DB_PASSWORD, SECRET_KEY, CORS_ORIGINS, VITE_API_URL
   ```
   Lưu ý:
   - `SECRET_KEY` ít nhất 32 ký tự (backend tự fail-fast nếu thiếu ở production).
   - `VITE_API_URL` là URL public của backend, VD `https://api.example.com/api`.
     Nó được "nướng" vào JS lúc build image frontend, đổi URL phải build lại image.
   - File `.env` thật KHÔNG commit lên git.

## 2. Pipeline tự động (GitHub Actions)

- **CI** (`.github/workflows/ci.yml`): chạy trên mọi push/PR —
  backend (`pytest`, kiểm tra Alembic single head), frontend (`tsc`, `lint`, `test`),
  PR còn build thử 2 image Docker.
- **CD** (`.github/workflows/cd.yml`): khi push lên `main` hoặc `develop` —
  build + push 2 image lên GHCR với tag `<nhánh>` và `<sha>` (riêng `main`
  có thêm tag `latest`). Job `deploy` về VPS chỉ chạy từ `main`
  (develop chỉ build image để test, không deploy production).

## 3. Bật deploy tự động về VPS (tùy chọn)

Đặt trong repo Settings → Secrets and variables → Actions:

| Loại | Tên | Ví dụ |
|---|---|---|
| Variable | `VPS_HOST` | `203.0.113.10` |
| Variable | `VPS_USER` | `deploy` |
| Variable | `VPS_PORT` | `22` (tùy chọn) |
| Variable | `VPS_APP_DIR` | `~/doantotnghiep` (tùy chọn) |
| Variable | `VITE_API_URL` | `https://api.example.com/api` |
| Secret | `VPS_SSH_KEY` | private key SSH tới VPS |

Trên VPS, thư mục app cần có `docker-compose.yml` + `.env`
(lấy từ repo, `.env` tự tạo theo `.env.deploy.example`).
GHCR package phải để visibility phù hợp để VPS pull được
(public, hoặc private + VPS đã `docker login` — workflow CD tự login khi deploy).

## 4. Deploy thủ công (không cần CD)

```bash
# Trên VPS, trong thư mục chứa docker-compose.yml + .env:
docker compose up -d --build
docker compose logs -f backend   # xem log migrate + khởi động
curl localhost:8000/health       # {"status":"ok"}
```

Backend tự chạy `alembic upgrade head` trước khi mở port —
DB cũ thiếu cột (vd `users.is_verified`) sẽ được migrate, không còn 503.

## 5. Cập nhật bản mới (dùng image GHCR)

```bash
BACKEND_IMAGE=ghcr.io/huyducn/doantotnghiep-backend:<sha> \
FRONTEND_IMAGE=ghcr.io/huyducn/doantotnghiep-frontend:<sha> \
docker compose pull backend frontend
BACKEND_IMAGE=ghcr.io/huyducn/doantotnghiep-backend:<sha> \
FRONTEND_IMAGE=ghcr.io/huyducn/doantotnghiep-frontend:<sha> \
docker compose up -d backend frontend
```

## 6. Sự cố thường gặp

| Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|
| Backend 503 `Unknown column` | DB chưa migrate | Compose đã tự migrate; kiểm tra `docker compose logs backend` |
| Backend 503 access-denied MySQL | Sai `DB_PASSWORD` | Sửa `.env`, `docker compose up -d db backend` |
| Frontend gọi API localhost | `VITE_API_URL` sai lúc build | Build lại image frontend với URL đúng |
| 413 khi upload CV | Reverse proxy chặn trước app | Mở `client_max_body_size 12m;` ở nginx ngoài (nếu có) |
