import { z } from 'zod';

const characterCount = (value: string) => Array.from(value).length;
const hasControls = (value: string, multiline = false) =>
  /[\p{Cc}\p{Cf}]/u.test(multiline ? value.replace(/[\r\n\t]/g, '') : value);

function profileText(label: string, limit: number, multiline = false) {
  return z.string().trim()
    .refine((value) => characterCount(value) <= limit, `${label} không được quá ${limit} ký tự`)
    .refine((value) => !hasControls(value, multiline), `${label} chứa ký tự điều khiển hoặc ký tự ẩn`);
}

export const fullNameSchema = profileText('Họ tên', 255).refine(
  (value) => value.length > 0, 'Họ tên không được để trống',
);

function validProfileUrl(value: string): boolean {
  if (!value) return true;
  if (!/^https?:\/\//i.test(value) || /\s|\\/.test(value) || !value.split('/')[2]) return false;
  try {
    const url = new URL(value);
    return Boolean(url.hostname) && !value.split('/')[2].includes('@') && !url.username && !url.password;
  } catch {
    return false;
  }
}

const profileUrl = (label: string) => profileText(label, 500).refine(
  validProfileUrl, 'Đường dẫn phải là URL http:// hoặc https:// hợp lệ, không kèm tài khoản/mật khẩu',
);

export const profileSchema = z.object({
  full_name: fullNameSchema,
  phone: profileText('Số điện thoại', 20).refine((value) => {
    if (!value) return true;
    const digits = value.replace(/[^0-9]/g, '').length;
    return /^\+?[0-9 ()-]+$/.test(value) && digits >= 7 && digits <= 15;
  }, 'Số điện thoại cần có 7–15 chữ số; chỉ dùng dấu + ở đầu, dấu cách, ngoặc hoặc gạch ngang'),
  location: profileText('Địa điểm', 255),
  job_title: profileText('Chức danh', 255),
  bio: profileText('Giới thiệu', 2000, true),
  linkedin_url: profileUrl('URL LinkedIn'),
  github_url: profileUrl('URL GitHub'),
});
