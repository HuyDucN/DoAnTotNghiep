import assert from 'node:assert/strict';
import test from 'node:test';
import { getCvMatchStatusInfo } from '../src/services/cvMatchStatus.ts';

test('chỉ xác nhận CV còn khớp khi API trả current', () => {
  assert.equal(getCvMatchStatusInfo('current').tone, 'success');
  for (const status of ['changed', 'processing', 'failed', 'unknown', undefined, null, 'invalid', 'toString']) {
    assert.notEqual(getCvMatchStatusInfo(status).tone, 'success');
  }
});

test('hướng dẫn chờ phân tích, xử lý lỗi và so khớp lại phù hợp từng trạng thái', () => {
  assert.match(getCvMatchStatusInfo('processing').description, /Chờ phân tích hoàn tất/);
  assert.match(getCvMatchStatusInfo('failed').description, /Phân tích lại CV thành công/);
  assert.match(getCvMatchStatusInfo('changed').description, /so khớp lại/);
  assert.match(getCvMatchStatusInfo('unknown').description, /Chưa đủ thông tin/);
  assert.deepEqual(getCvMatchStatusInfo(undefined), getCvMatchStatusInfo('unknown'));
});
