import assert from 'node:assert/strict';
import test from 'node:test';
import { isCancelledError, QueryClient, QueryObserver } from '@tanstack/react-query';
import { getRecordedMatchResult } from '../src/pages/jobs/matchRequest.ts';
import {
  myCvsKey, refreshCompletedCvs, syncCvAnalysisStarted,
  syncCvDeleted, syncCvSkillDeleted, syncCvSkillSaved,
} from '../src/services/cvCache.ts';

const historyKey = ['skill-gaps', 'mine'];
const cv = (status = 'analyzed') => ({ id: 10, user_id: 4, filename: 'cv.pdf', status });
const saved = () => ({
  id: 90, cv_id: 10, cv_filename: 'cv.pdf', cv_match_status: 'current',
  job: { id: 1, title: 'Backend' }, match_score: 80,
});
const accepted = (result = saved()) => ({ request: { requestId: 1, jobId: 1, cvId: 10 }, result });
const visible = (outcome, cache, cvId = 10) => getRecordedMatchResult(outcome, 1, cvId, cache.getQueryData(historyKey));
const client = () => new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity, gcTime: Infinity } } });
const tick = () => new Promise((resolve) => setImmediate(resolve));

function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}

test('chưa tải được bản đã lưu thì không dùng lại nhãn current từ phản hồi POST', () => {
  const outcome = accepted();
  assert.equal(getRecordedMatchResult(outcome, 1, 10, undefined), null);
  assert.equal(getRecordedMatchResult(outcome, 1, 10, []), null);
  assert.equal(getRecordedMatchResult(null, 1, 10, [saved()]), null);
});

test('trang So khớp hiển thị điểm và trạng thái từ lịch sử đã cập nhật', () => {
  const outcome = accepted();
  const currentRecord = { ...saved(), match_score: 95, cv_match_status: 'changed' };
  assert.equal(getRecordedMatchResult(outcome, 1, 10, [currentRecord]), currentRecord);
  assert.equal(outcome.result.cv_match_status, 'current');
  assert.equal(outcome.result.match_score, 80);
});

for (const [field, record] of [
  ['mã kết quả', { ...saved(), id: 91 }],
  ['CV', { ...saved(), cv_id: 20 }],
  ['công việc', { ...saved(), job: { id: 2 } }],
]) {
  test(`bản lịch sử sai ${field} không được gắn vào kết quả đang chọn`, () => {
    assert.equal(getRecordedMatchResult(accepted(), 1, 10, [record]), null);
  });
}

test('đổi lựa chọn không hiển thị kết quả cũ dù lịch sử vẫn còn bản ghi', () => {
  const outcome = accepted();
  assert.equal(getRecordedMatchResult(outcome, 1, 20, [saved()]), null);
  assert.equal(getRecordedMatchResult(outcome, 2, 10, [saved()]), null);
  assert.equal(getRecordedMatchResult(outcome, 1, '', [saved()]), null);
});

test('phân tích lại rồi hoàn tất không khôi phục nhãn current của bản sao cũ', async () => {
  const cache = client();
  const outcome = accepted();
  try {
    cache.setQueryData(myCvsKey, [cv()]);
    cache.setQueryData(historyKey, [saved()]);
    await syncCvAnalysisStarted(cache, cv('uploaded'));
    assert.equal(visible(outcome, cache, ''), null);
    assert.equal(visible(outcome, cache).cv_match_status, 'processing');
    await refreshCompletedCvs(cache, [10]);
    cache.setQueryData(myCvsKey, [cv()]);
    assert.equal(visible(outcome, cache).cv_match_status, 'unknown');
    cache.setQueryData(historyKey, [{ ...saved(), cv_match_status: 'changed' }]);
    assert.equal(visible(outcome, cache).cv_match_status, 'changed');
    assert.equal(outcome.result.cv_match_status, 'current');
  } finally { cache.clear(); }
});

for (const [action, change] of [
  ['lưu kỹ năng', (cache) => syncCvSkillSaved(cache, 10, { skill_id: 1, source: 'manual' })],
  ['xóa kỹ năng', (cache) => syncCvSkillDeleted(cache, 10, 1)],
]) {
  test(`${action} cập nhật trạng thái ngay trên kết quả So khớp`, async () => {
    const cache = client();
    const outcome = accepted();
    try {
      cache.setQueryData(historyKey, [saved()]);
      await change(cache);
      assert.equal(visible(outcome, cache).cv_match_status, 'unknown');
      assert.equal(visible(outcome, cache).match_score, 80);
      cache.setQueryData(historyKey, [{ ...saved(), cv_match_status: 'changed' }]);
      assert.equal(visible(outcome, cache).cv_match_status, 'changed');
    } finally { cache.clear(); }
  });
}

test('xóa CV làm mất kết quả trên trang So khớp thay vì dùng lại phản hồi POST', async () => {
  const cache = client();
  try {
    cache.setQueryData(myCvsKey, [cv()]);
    cache.setQueryData(historyKey, [saved()]);
    await syncCvDeleted(cache, 10);
    assert.equal(visible(accepted(), cache), null);
  } finally { cache.clear(); }
});

test('so khớp lại bỏ điểm cũ trong cache và chặn lượt đọc trước lần lưu mới', async () => {
  const cache = client();
  const lateRead = deferred();
  const oldRecord = { ...saved(), match_score: 10 };
  const outcome = accepted({ ...saved(), match_score: 95 });
  try {
    cache.setQueryData(historyKey, [oldRecord]);
    const oldRequest = cache.fetchQuery({ queryKey: historyKey, staleTime: 0, queryFn: () => lateRead.promise });
    const settled = Promise.allSettled([oldRequest]);
    await cache.resetQueries({ queryKey: historyKey, exact: true });
    assert.equal(visible(outcome, cache), null);
    await cache.fetchQuery({ queryKey: historyKey, queryFn: async () => [outcome.result] });
    lateRead.resolve([oldRecord]);
    const [result] = await settled;
    assert.ok(result.status === 'fulfilled' || isCancelledError(result.reason));
    await tick();
    assert.equal(visible(outcome, cache).match_score, 95);
  } finally { cache.clear(); }
});

test('tải kết quả lỗi rồi thử GET lại không hiển thị bản sao POST trong lúc chờ', async () => {
  const cache = client();
  let reads = 0;
  const outcome = accepted();
  const observer = new QueryObserver(cache, {
    queryKey: historyKey, enabled: false,
    queryFn: async () => { reads++; if (reads === 1) throw new Error('Network unavailable'); return [saved()]; },
  });
  const stop = observer.subscribe(() => {});
  try {
    await observer.refetch();
    assert.equal(observer.getCurrentResult().isError, true);
    assert.equal(visible(outcome, cache), null);
    await observer.refetch();
    assert.equal(reads, 2);
    assert.deepEqual(visible(outcome, cache), saved());
  } finally { stop(); observer.destroy(); cache.clear(); }
});

test('bật query sau so khớp chỉ hiển thị bản được tải sau khi đặt lại lịch sử', async () => {
  const cache = client();
  const freshRead = deferred();
  const outcome = accepted({ ...saved(), match_score: 95 });
  const options = { queryKey: historyKey, queryFn: () => freshRead.promise };
  const observer = new QueryObserver(cache, { ...options, enabled: false });
  const stop = observer.subscribe(() => {});
  try {
    cache.setQueryData(historyKey, [{ ...saved(), match_score: 10 }]);
    await cache.resetQueries({ queryKey: historyKey, exact: true });
    observer.setOptions({ ...options, enabled: true });
    assert.equal(observer.getCurrentResult().isFetching, true);
    assert.equal(visible(outcome, cache), null);
    const loaded = observer.refetch();
    freshRead.resolve([outcome.result]);
    await loaded;
    assert.equal(visible(outcome, cache).match_score, 95);
  } finally { stop(); observer.destroy(); cache.clear(); }
});
