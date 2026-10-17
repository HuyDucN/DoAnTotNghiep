-- Migration 004: Thêm role employer cho tài khoản Nhà tuyển dụng.
ALTER TABLE users
    MODIFY COLUMN role ENUM('user', 'admin', 'employer') NOT NULL DEFAULT 'user';
