import assert from 'node:assert/strict';
import test from 'node:test';
import { fullNameSchema, profileSchema } from '../src/validation/account.ts';

const validProfile = {
  full_name: 'Nguyễn Thị Ánh', phone: '', location: '', job_title: '', bio: '', linkedin_url: '', github_url: '',
};

test('tên đăng ký và tên hồ sơ dùng chung quy tắc, giữ dấu tiếng Việt', () => {
  assert.equal(fullNameSchema.parse('  Nguyễn Thị Ánh  '), 'Nguyễn Thị Ánh');
  assert.equal(fullNameSchema.parse('A'), 'A');
  for (const name of ['', '   ', '\u00a0', 'x'.repeat(256), '🙂'.repeat(256), 'Tên\u200bẩn', 'Tên\x00ẩn', 'Tên\nkhác']) {
    assert.equal(fullNameSchema.safeParse(name).success, false, JSON.stringify(name));
    assert.equal(profileSchema.safeParse({ ...validProfile, full_name: name }).success, false);
  }
});

test('giới hạn tính theo ký tự Unicode và phù hợp giới hạn API', () => {
  const url = 'https://example.com/' + 'x'.repeat(500 - 'https://example.com/'.length);
  assert.equal(fullNameSchema.parse('🙂'.repeat(255)), '🙂'.repeat(255));
  assert.equal(profileSchema.safeParse({
    ...validProfile, location: 'Á'.repeat(255), job_title: '🙂'.repeat(255), bio: 'Á'.repeat(2000), github_url: url,
  }).success, true);
  for (const [field, value] of [['location', 'x'.repeat(256)], ['job_title', 'x'.repeat(256)], ['bio', 'x'.repeat(2001)], ['github_url', `${url}x`], ['linkedin_url', `${url}x`]]) {
    const result = profileSchema.safeParse({ ...validProfile, [field]: value });
    assert.equal(result.success, false, field);
    assert.equal(result.error.issues[0].path[0], field);
  }
});

test('số điện thoại cần có chữ số thực và dấu cộng chỉ nằm ở đầu', () => {
  for (const phone of ['+++++++', '(---)---', '123456', '1'.repeat(16), '090123abc7', '090+1234567', '٠٩٠١٢٣٤٥٦٧', '090\n1234567']) {
    assert.equal(profileSchema.safeParse({ ...validProfile, phone }).success, false, phone);
  }
  for (const phone of ['', '0901234567', '+84 (90) 123-4567', '+123456789012345']) {
    assert.equal(profileSchema.safeParse({ ...validProfile, phone }).success, true, phone);
  }
});

test('URL hồ sơ phải đầy đủ, dùng HTTP(S) và không chứa thông tin đăng nhập', () => {
  for (const field of ['github_url', 'linkedin_url']) {
    for (const value of ['https://', 'https:///github.com/dev', 'javascript:alert(1)', 'ftp://example.com/profile', 'https://user:pass@example.com', 'https://@example.com', 'https://example.com/white space', 'https://example.com\\path', 'https://example.com:99999/profile', 'https://[invalid']) {
      assert.equal(profileSchema.safeParse({ ...validProfile, [field]: value }).success, false, `${field}: ${value}`);
    }
    for (const value of ['', 'https://github.com/dev', 'https://www.linkedin.com/in/example?lang=vi#intro', 'http://example.com/profile']) {
      assert.equal(profileSchema.safeParse({ ...validProfile, [field]: value }).success, true, `${field}: ${value}`);
    }
  }
});

test('giới thiệu cho phép xuống dòng, trường một dòng từ chối ký tự điều khiển', () => {
  const data = profileSchema.parse({ ...validProfile, location: '  Đà Nẵng  ', bio: ' Dòng 1\nDòng 2\tghi chú ' });
  assert.equal(data.location, 'Đà Nẵng');
  assert.equal(data.bio, 'Dòng 1\nDòng 2\tghi chú');
  for (const [field, value] of [['location', 'Hà\nNội'], ['job_title', 'Dev\u200bOps'], ['bio', 'Text\x00hidden']]) {
    assert.equal(profileSchema.safeParse({ ...validProfile, [field]: value }).success, false, field);
  }
});
