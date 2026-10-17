-- Migration 002: Soft Delete cho bảng jobs và skills
-- Tác giả: AI Antigravity
-- Ngày: 2026-10-05
-- Mô tả: Thêm cột is_deleted (TINYINT/BOOLEAN) và deleted_at (DATETIME)
--         vào bảng jobs và skills để hỗ trợ Soft Delete.
--         Dữ liệu cũ sẽ có is_deleted = 0 (FALSE) mặc định.

-- ────────────────────────────────────────────────────────────────────────────
-- Bảng: jobs
-- ────────────────────────────────────────────────────────────────────────────
ALTER TABLE jobs
    ADD COLUMN is_deleted  TINYINT(1) NOT NULL DEFAULT 0     COMMENT 'Soft Delete: 1 = đã xóa mềm',
    ADD COLUMN deleted_at  DATETIME   NULL     DEFAULT NULL   COMMENT 'Thời điểm xóa mềm (UTC)';

-- Index để query nhanh hơn (lọc is_deleted = 0 trong hầu hết mọi truy vấn)
CREATE INDEX idx_jobs_is_deleted ON jobs (is_deleted);

-- ────────────────────────────────────────────────────────────────────────────
-- Bảng: skills
-- ────────────────────────────────────────────────────────────────────────────
ALTER TABLE skills
    ADD COLUMN is_deleted  TINYINT(1) NOT NULL DEFAULT 0     COMMENT 'Soft Delete: 1 = đã xóa mềm',
    ADD COLUMN deleted_at  DATETIME   NULL     DEFAULT NULL   COMMENT 'Thời điểm xóa mềm (UTC)';

-- Index để query nhanh hơn
CREATE INDEX idx_skills_is_deleted ON skills (is_deleted);
