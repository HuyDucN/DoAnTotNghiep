import assert from 'node:assert/strict';
import test from 'node:test';
import { QueryClient, QueryObserver, focusManager } from '@tanstack/react-query';
import { createCvForegroundRefresh } from '../src/services/foregroundCvRefresh.ts';

const historyKey = ['skill-gaps', 'mine'];
const original = [{ id: 90, cv_id: 10, match_score: 80, cv_match_status: 'current' }];
const updated = [{ id: 90, cv_id: 10, match_score: 80, cv_match_status: 'changed' }];
const tick = () => new Promise((resolve) => setImmediate(resolve));

function client() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 30_000, gcTime: Infinity } },
  });
}

test('refresh khi quay lại tab lấy trạng thái CV mới cho query đang mở', async () => {
  const cache = client();
  cache.setQueryData(historyKey, original);
  let reads = 0;
  const observer = new QueryObserver(cache, {
    queryKey: historyKey,
    queryFn: async () => { reads++; return updated; },
  });
  const stop = observer.subscribe(() => {});
  const foreground = createCvForegroundRefresh(cache);
  try {
    assert.equal(reads, 0);
    assert.equal(observer.getCurrentResult().isStale, false);
    await foreground.refresh();
    assert.deepEqual(cache.getQueryData(historyKey), updated);
    assert.equal(observer.getCurrentResult().isError, false);
    assert.equal(reads, 1);
  } finally {
    foreground.dispose();
    stop();
    observer.destroy();
    cache.clear();
  }
});

test('refresh đánh dấu trạng thái cũ là unknown ngay cả khi query chưa mở', async () => {
  const cache = client();
  const foreground = createCvForegroundRefresh(cache);
  try {
    cache.setQueryData(historyKey, original);
    await foreground.refresh();
    assert.deepEqual(cache.getQueryData(historyKey), [{ ...original[0], cv_match_status: 'unknown' }]);
    assert.equal(cache.getQueryState(historyKey).isInvalidated, true);
  } finally {
    foreground.dispose();
    cache.clear();
  }
});

test('focus listener được dọn, phiên cũ không làm thay đổi cache sau dispose', async () => {
  const cache = client();
  const foreground = createCvForegroundRefresh(cache);
  cache.setQueryData(historyKey, original);
  foreground.dispose();
  focusManager.setFocused(false);
  focusManager.setFocused(true);
  await tick();
  assert.deepEqual(cache.getQueryData(historyKey), original);
  cache.clear();
  focusManager.setFocused(undefined);
});

test('phản hồi được gửi trước lúc trở lại tab không ghi đè trạng thái mới', { timeout: 3000 }, async () => {
  const cache = client();
  cache.setQueryData(historyKey, original);
  let resolveOld;
  const oldResponse = new Promise((resolve) => { resolveOld = resolve; });
  let reads = 0;
  const observer = new QueryObserver(cache, {
    queryKey: historyKey,
    queryFn: () => ++reads === 1 ? oldResponse : Promise.resolve(updated),
  });
  const stop = observer.subscribe(() => {});
  const foreground = createCvForegroundRefresh(cache);
  try {
    const previous = observer.refetch();
    assert.equal(reads, 1);
    await foreground.refresh();
    assert.equal(reads, 2);
    assert.deepEqual(observer.getCurrentResult().data, updated);
    resolveOld([{ ...original[0], match_score: 1 }]);
    await previous;
    await tick();
    assert.deepEqual(cache.getQueryData(historyKey), updated);
  } finally {
    resolveOld(original);
    foreground.dispose();
    stop();
    observer.destroy();
    cache.clear();
  }
});

test('mạng lỗi khi trở lại tab giữ điểm và bỏ nhãn xác nhận CV cũ', async () => {
  const cache = client();
  cache.setQueryData(historyKey, original);
  const observer = new QueryObserver(cache, {
    queryKey: historyKey, queryFn: async () => { throw new Error('Network unavailable'); },
  });
  const stop = observer.subscribe(() => {});
  const foreground = createCvForegroundRefresh(cache);
  try {
    await foreground.refresh();
    assert.equal(observer.getCurrentResult().isError, true);
    assert.deepEqual(cache.getQueryData(historyKey), [{ ...original[0], cv_match_status: 'unknown' }]);
  } finally {
    foreground.dispose();
    stop();
    observer.destroy();
    cache.clear();
  }
});

test('trở lại tab tải đủ dữ liệu CV còn mới và chỉ đánh dấu kỹ năng chưa mở', async () => {
  const cache = client();
  const oldValues = [
    [['cvs', 'mine'], [{ id: 10, status: 'analyzed' }]],
    [['cv-skills', 10], [{ skill_id: 1, proficiency_level: 'beginner' }]],
    [['cv-status', 10], { id: 10, status: 'analyzed' }],
    [historyKey, original],
    [['jobs', { page: 1 }], { total: 3 }],
  ];
  const freshValues = [
    [{ id: 10, status: 'processing' }], [{ skill_id: 1, proficiency_level: 'expert' }],
    { id: 10, status: 'processing' }, updated, { total: 99 },
  ];
  const reads = oldValues.map(() => 0);
  const observers = oldValues.map(([queryKey, value], index) => {
    cache.setQueryData(queryKey, value);
    return new QueryObserver(cache, {
      queryKey, queryFn: async () => { reads[index]++; return freshValues[index]; },
    });
  });
  const stops = observers.map((observer) => observer.subscribe(() => {}));
  const foreground = createCvForegroundRefresh(cache);
  try {
    cache.setQueryData(['cv-skills', 20], [{ skill_id: 2 }]);
    assert.deepEqual(reads, [0, 0, 0, 0, 0]);
    await foreground.refresh();
    assert.deepEqual(reads, [1, 1, 1, 1, 0]);
    for (let index = 0; index < 4; index++) {
      assert.deepEqual(observers[index].getCurrentResult().data, freshValues[index]);
    }
    assert.deepEqual(observers[4].getCurrentResult().data, { total: 3 });
    assert.equal(cache.getQueryState(['cv-skills', 20]).isInvalidated, true);
  } finally {
    foreground.dispose();
    stops.forEach((stop) => stop());
    observers.forEach((observer) => observer.destroy());
    cache.clear();
  }
});

test('đóng phiên khi refresh đang hủy request không khôi phục cache đã xóa', async () => {
  const first = client();
  const second = client();
  first.setQueryData(historyKey, original);
  second.setQueryData(historyKey, updated);
  const foreground = createCvForegroundRefresh(first);
  try {
    const pending = foreground.refresh();
    foreground.dispose();
    first.clear();
    await pending;
    assert.equal(first.getQueryCache().getAll().length, 0);
    assert.deepEqual(second.getQueryData(historyKey), updated);
  } finally {
    foreground.dispose();
    first.clear();
    second.clear();
  }
});

test('chỉ sự kiện tab trở lại hiển thị mới kích hoạt đọc, tab ẩn giữ nguyên cache', async () => {
  const cache = client();
  cache.setQueryData(historyKey, original);
  let reads = 0;
  focusManager.setFocused(false);
  const observer = new QueryObserver(cache, {
    queryKey: historyKey, queryFn: async () => { reads++; return updated; },
  });
  const stop = observer.subscribe(() => {});
  const foreground = createCvForegroundRefresh(cache);
  try {
    focusManager.onFocus();
    await tick();
    assert.equal(reads, 0);
    focusManager.setFocused(true);
    await tick();
    assert.equal(reads, 1);
    assert.deepEqual(cache.getQueryData(historyKey), updated);
  } finally {
    foreground.dispose();
    stop();
    observer.destroy();
    cache.clear();
    focusManager.setFocused(undefined);
  }
});

test('nhiều lần quay lại tab không tạo dữ liệu CV cũ trong cache', async () => {
  const cache = client();
  const foreground = createCvForegroundRefresh(cache);
  try {
    cache.setQueryData(historyKey, original);
    await Promise.all([foreground.refresh(), foreground.refresh(), foreground.refresh()]);
    assert.deepEqual(cache.getQueryData(historyKey), [{ ...original[0], cv_match_status: 'unknown' }]);
  } finally {
    foreground.dispose();
    cache.clear();
  }
});
