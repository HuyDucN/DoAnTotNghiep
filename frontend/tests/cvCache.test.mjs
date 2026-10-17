import assert from 'node:assert/strict';
import test from 'node:test';
import { isCancelledError, QueryClient, QueryObserver } from '@tanstack/react-query';
import {
  cvCompletionKey, cvSkillsKey, cvStatusKey, myCvsKey,
  refreshCompletedCvs, syncCvAnalysisStarted, syncCvDeleted,
  syncCvSkillDeleted, syncCvSkillSaved,
} from '../src/services/cvCache.ts';

function client() {
  return new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity, gcTime: Infinity } } });
}

function cv(id, status = 'analyzed') {
  return { id, status, user_id: 4, filename: `CV-${id}.pdf`, created_at: '2026-10-16', ai_analysis: status === 'analyzed' ? { summary: `Result ${id}` } : null };
}

function deferred() {
  let resolve;
  const promise = new Promise((ok) => { resolve = ok; });
  return { promise, resolve };
}

const tick = () => new Promise((resolve) => setImmediate(resolve));
const historyKey = ['skill-gaps', 'mine'];

test('xóa CV loại bỏ dữ liệu phụ thuộc và giữ nguyên các CV khác', async () => {
  const cache = client();
  try {
    cache.setQueryData(myCvsKey, [cv(1), cv(2)]);
    cache.setQueryData(cvStatusKey(1), { id: 1, status: 'processing' });
    cache.setQueryData(cvSkillsKey(1), [{ skill_id: 10, source: 'manual' }]);
    cache.setQueryData(cvSkillsKey(2), [{ skill_id: 20 }]);
    cache.setQueryData(historyKey, [{ id: 90, match_score: 50 }]);
    cache.setQueryData(['admin', 'cvs', 1], { items: [cv(1)], total: 1 });
    cache.setQueryData(['admin', 'users'], { total: 5 });
    await syncCvDeleted(cache, 1);
    assert.deepEqual(cache.getQueryData(myCvsKey), [cv(2)]);
    assert.equal(cache.getQueryData(cvStatusKey(1)), undefined);
    assert.equal(cache.getQueryData(cvSkillsKey(1)), undefined);
    assert.deepEqual(cache.getQueryData(cvSkillsKey(2)), [{ skill_id: 20 }]);
    assert.equal(cache.getQueryData(historyKey), undefined);
    assert.equal(cache.getQueryState(myCvsKey).isInvalidated, true);
    assert.equal(cache.getQueryState(['admin', 'cvs', 1]).isInvalidated, true);
    assert.equal(cache.getQueryState(['admin', 'users']).isInvalidated, false);
  } finally { cache.clear(); }
});

test('phản hồi danh sách và báo cáo về muộn không khôi phục CV đã xóa', async () => {
  const cache = client();
  const reads = [deferred(), deferred(), deferred(), deferred()];
  try {
    cache.setQueryData(myCvsKey, [cv(1), cv(2)]);
    cache.setQueryData(historyKey, [{ id: 90 }]);
    const queries = [myCvsKey, historyKey, cvStatusKey(1), cvSkillsKey(1)];
    const requests = queries.map((queryKey, index) => cache.fetchQuery({ queryKey, staleTime: 0, queryFn: () => reads[index].promise }));
    const settled = Promise.allSettled(requests);
    await syncCvDeleted(cache, 1);
    reads[0].resolve([cv(1), cv(2)]);
    reads[1].resolve([{ id: 90 }]);
    reads[2].resolve({ id: 1, status: 'analyzed' });
    reads[3].resolve([{ skill_id: 10 }]);
    const results = await settled;
    assert.ok(results.every((result) => result.status === 'fulfilled' || isCancelledError(result.reason)));
    await tick();
    assert.deepEqual(cache.getQueryData(myCvsKey), [cv(2)]);
    assert.equal(cache.getQueryData(historyKey), undefined);
    assert.equal(cache.getQueryData(cvSkillsKey(1)), undefined);
    assert.equal(cache.getQueryData(cvStatusKey(1)), undefined);
  } finally { cache.clear(); }
});

test('Dashboard và Báo cáo đang mở tải lại lịch sử từ server sau xóa', async () => {
  const cache = client();
  const serverHistory = [{ id: 91, match_score: 75 }];
  const observer = new QueryObserver(cache, { queryKey: historyKey, queryFn: async () => serverHistory });
  let unsubscribe;
  try {
    cache.setQueryData(historyKey, [{ id: 90, match_score: 20 }, ...serverHistory]);
    unsubscribe = observer.subscribe(() => {});
    await syncCvDeleted(cache, 1);
    assert.deepEqual(observer.getCurrentResult().data, serverHistory);
    assert.deepEqual(cache.getQueryData(historyKey), serverHistory);
  } finally { unsubscribe?.(); observer.destroy(); cache.clear(); }
});

test('bắt đầu phân tích lại đặt lại status cũ và giữ thứ tự danh sách', async () => {
  const cache = client();
  try {
    cache.setQueryData(myCvsKey, [cv(2), cv(1)]);
    cache.setQueryData(cvStatusKey(1), { id: 1, status: 'analyzed' });
    const queued = cv(1, 'uploaded');
    await syncCvAnalysisStarted(cache, queued);
    assert.deepEqual(cache.getQueryData(myCvsKey), [cv(2), queued]);
    assert.deepEqual(cache.getQueryData(cvStatusKey(1)), { id: 1, status: 'uploaded' });
    assert.equal(cvCompletionKey(0, [{ data: cache.getQueryData(cvStatusKey(1)), dataUpdatedAt: 100 }]), '');
    await syncCvAnalysisStarted(cache, cv(3, 'uploaded'));
    assert.deepEqual(cache.getQueryData(myCvsKey).map((item) => item.id), [3, 2, 1]);
  } finally { cache.clear(); }
});

test('phản hồi status của lần trước không ghi đè trạng thái lần mới', async () => {
  const cache = client();
  const network = deferred();
  try {
    cache.setQueryData(myCvsKey, [cv(1)]);
    cache.setQueryData(cvStatusKey(1), { id: 1, status: 'analyzed' });
    const old = cache.fetchQuery({ queryKey: cvStatusKey(1), staleTime: 0, queryFn: () => network.promise });
    const settled = Promise.allSettled([old]);
    await syncCvAnalysisStarted(cache, cv(1, 'uploaded'));
    network.resolve({ id: 1, status: 'failed' });
    await settled;
    await tick();
    assert.equal(cache.getQueryData(cvStatusKey(1)).status, 'uploaded');
    assert.equal(cache.getQueryData(myCvsKey)[0].status, 'uploaded');
  } finally { cache.clear(); }
});

test('terminal status cũ bị bỏ qua, thành công và thất bại mới đều làm mới dữ liệu', () => {
  const reads = [
    { data: { id: 1, status: 'analyzed' }, dataUpdatedAt: 90 },
    { data: { id: 2, status: 'analyzed' }, dataUpdatedAt: 110 },
    { data: { id: 3, status: 'failed' }, dataUpdatedAt: 120 },
    { data: { id: 4, status: 'processing' }, dataUpdatedAt: 130 },
    { data: undefined, dataUpdatedAt: 0 },
  ];
  assert.equal(cvCompletionKey(100, reads), '2:110|3:120');
  assert.equal(cvCompletionKey(140, reads), '');
});

test('hoàn tất phân tích làm mới trạng thái đối chiếu, giữ nguyên điểm đã lưu', async () => {
  const cache = client();
  try {
    cache.setQueryData(myCvsKey, [cv(1, 'processing'), cv(2)]);
    cache.setQueryData(cvSkillsKey(1), [{ skill_id: 10, source: 'manual' }]);
    cache.setQueryData(cvSkillsKey(2), [{ skill_id: 20 }]);
    cache.setQueryData(historyKey, [{ id: 90, cv_id: 1, match_score: 50, cv_match_status: 'processing' }]);
    await refreshCompletedCvs(cache, [1, 1]);
    assert.equal(cache.getQueryState(myCvsKey).isInvalidated, true);
    assert.equal(cache.getQueryState(cvSkillsKey(1)).isInvalidated, true);
    assert.equal(cache.getQueryState(cvSkillsKey(2)).isInvalidated, false);
    assert.deepEqual(cache.getQueryData(historyKey), [{ id: 90, cv_id: 1, match_score: 50, cv_match_status: 'unknown' }]);
    assert.equal(cache.getQueryState(historyKey).isInvalidated, true);
  } finally { cache.clear(); }
});

test('kỹ năng được đọc trước khi AI hoàn tất không ghi đè lần tải mới', async () => {
  const cache = client();
  const network = deferred();
  const fresh = [{ skill_id: 11, source: 'ai_extracted' }, { skill_id: 10, source: 'manual' }];
  const observer = new QueryObserver(cache, { queryKey: cvSkillsKey(1), queryFn: () => network.promise });
  let unsubscribe;
  try {
    const old = cache.fetchQuery({ queryKey: cvSkillsKey(1), queryFn: () => network.promise });
    const canceled = assert.rejects(old, isCancelledError);
    await refreshCompletedCvs(cache, [1]);
    observer.setOptions({ queryKey: cvSkillsKey(1), queryFn: async () => fresh });
    unsubscribe = observer.subscribe(() => {});
    await observer.refetch();
    network.resolve([{ skill_id: 9 }]);
    await canceled;
    await tick();
    assert.deepEqual(cache.getQueryData(cvSkillsKey(1)), fresh);
  } finally { unsubscribe?.(); observer.destroy(); cache.clear(); }
});

test('đổi CV trong hồ sơ không nhận phản hồi kỹ năng của CV trước', async () => {
  const cache = client();
  const firstRead = deferred();
  const observer = new QueryObserver(cache, { queryKey: cvSkillsKey(1), queryFn: () => firstRead.promise });
  const unsubscribe = observer.subscribe(() => {});
  try {
    observer.setOptions({ queryKey: cvSkillsKey(2), queryFn: async () => [{ skill_id: 20 }] });
    await observer.refetch();
    firstRead.resolve([{ skill_id: 10 }]);
    await tick();
    assert.deepEqual(observer.getCurrentResult().data, [{ skill_id: 20 }]);
    assert.deepEqual(cache.getQueryData(cvSkillsKey(2)), [{ skill_id: 20 }]);
  } finally { unsubscribe(); observer.destroy(); cache.clear(); }
});

test('cache thuộc phiên khác không bị thay đổi khi xóa CV', async () => {
  const first = client();
  const second = client();
  try {
    first.setQueryData(myCvsKey, [cv(1)]);
    second.setQueryData(myCvsKey, [cv(1), cv(2)]);
    second.setQueryData(historyKey, [{ id: 99 }]);
    await syncCvDeleted(first, 1);
    assert.deepEqual(second.getQueryData(myCvsKey), [cv(1), cv(2)]);
    assert.deepEqual(second.getQueryData(historyKey), [{ id: 99 }]);
  } finally { first.clear(); second.clear(); }
});

test('chưa có danh sách đầy đủ thì phản hồi một CV không tạo danh sách giả', async () => {
  const cache = client();
  try {
    await syncCvAnalysisStarted(cache, cv(1, 'uploaded'));
    assert.equal(cache.getQueryData(myCvsKey), undefined);
    assert.deepEqual(cache.getQueryData(cvStatusKey(1)), { id: 1, status: 'uploaded' });
    await syncCvDeleted(cache, 1);
    assert.equal(cache.getQueryData(myCvsKey), undefined);
    assert.equal(cache.getQueryData(cvStatusKey(1)), undefined);
  } finally { cache.clear(); }
});

test('phân tích hoàn tất ngay vẫn tải kỹ năng mới khi mở hồ sơ', async () => {
  const cache = client();
  const listObserver = new QueryObserver(cache, { queryKey: myCvsKey, queryFn: async () => [cv(1)] });
  const skillsObserver = new QueryObserver(cache, { queryKey: cvSkillsKey(1), queryFn: async () => [{ skill_id: 11 }] });
  let stopList;
  let stopSkills;
  try {
    cache.setQueryData(myCvsKey, [cv(1)]);
    cache.setQueryData(cvSkillsKey(1), [{ skill_id: 10 }]);
    stopList = listObserver.subscribe(() => {});
    await syncCvAnalysisStarted(cache, cv(1, 'uploaded'));
    assert.equal(cache.getQueryData(myCvsKey)[0].status, 'analyzed');
    assert.equal(cache.getQueryState(cvSkillsKey(1)).isInvalidated, true);
    stopSkills = skillsObserver.subscribe(() => {});
    await skillsObserver.refetch();
    assert.deepEqual(skillsObserver.getCurrentResult().data, [{ skill_id: 11 }]);
  } finally { stopList?.(); stopSkills?.(); listObserver.destroy(); skillsObserver.destroy(); cache.clear(); }
});

for (const action of ['save', 'delete']) {
  test(`kỹ năng đã ${action === 'save' ? 'lưu' : 'xóa'} vẫn hiển thị đúng nếu lần tải lại gặp lỗi mạng`, async () => {
    const cache = client();
    const existing = { skill_id: 10, source: 'ai_extracted', proficiency_level: 'beginner' };
    const saved = { skill_id: 10, source: 'manual', proficiency_level: 'expert' };
    const observer = new QueryObserver(cache, {
      queryKey: cvSkillsKey(1), queryFn: async () => { throw new Error('Network unavailable'); },
    });
    let unsubscribe;
    try {
      cache.setQueryData(cvSkillsKey(1), [existing]);
      cache.setQueryData(cvSkillsKey(2), [{ skill_id: 20 }]);
      unsubscribe = observer.subscribe(() => {});
      if (action === 'save') await syncCvSkillSaved(cache, 1, saved);
      else await syncCvSkillDeleted(cache, 1, 10);
      assert.deepEqual(observer.getCurrentResult().data, action === 'save' ? [saved] : []);
      assert.deepEqual(cache.getQueryData(cvSkillsKey(2)), [{ skill_id: 20 }]);
    } finally { unsubscribe?.(); observer.destroy(); cache.clear(); }
  });
}

const cvChanges = [
  ['phân tích lại', (cache) => syncCvAnalysisStarted(cache, cv(1, 'uploaded')), 'processing'],
  ['hoàn tất phân tích', (cache) => refreshCompletedCvs(cache, [1]), 'unknown'],
  ['lưu kỹ năng', (cache) => syncCvSkillSaved(cache, 1, { skill_id: 10, source: 'manual' }), 'unknown'],
  ['xóa kỹ năng', (cache) => syncCvSkillDeleted(cache, 1, 10), 'unknown'],
];

for (const [action, change, interimStatus] of cvChanges) {
  test(`${action}: báo cáo về muộn không khôi phục trạng thái CV đã cũ`, async () => {
    const cache = client();
    const oldRead = deferred();
    const original = [
      { id: 90, cv_id: 1, match_score: 50, cv_match_status: 'current' },
      { id: 91, cv_id: 2, match_score: 80, cv_match_status: 'current' },
    ];
    try {
      cache.setQueryData(historyKey, original);
      const request = cache.fetchQuery({ queryKey: historyKey, staleTime: 0, queryFn: () => oldRead.promise });
      const settled = Promise.allSettled([request]);
      await change(cache);
      oldRead.resolve(original);
      const [result] = await settled;
      assert.ok(result.status === 'fulfilled' || isCancelledError(result.reason));
      await tick();
      assert.deepEqual(cache.getQueryData(historyKey), [
        { ...original[0], cv_match_status: interimStatus }, original[1],
      ]);
      assert.equal(cache.getQueryState(historyKey).isInvalidated, true);
    } finally { cache.clear(); }
  });

  test(`${action}: Dashboard và Báo cáo lấy lại trạng thái được server xác nhận`, async () => {
    const cache = client();
    const old = { id: 90, cv_id: 1, match_score: 50, cv_match_status: 'current' };
    const updated = { ...old, cv_match_status: action === 'phân tích lại' ? 'processing' : 'changed' };
    const observer = new QueryObserver(cache, { queryKey: historyKey, queryFn: async () => [updated] });
    let unsubscribe;
    try {
      cache.setQueryData(historyKey, [old]);
      unsubscribe = observer.subscribe(() => {});
      await change(cache);
      assert.deepEqual(observer.getCurrentResult().data, [updated]);
      assert.equal(cache.getQueryState(historyKey).isInvalidated, false);
    } finally { unsubscribe?.(); observer.destroy(); cache.clear(); }
  });
}

test('sửa kỹ năng thành công nhưng tải lại báo cáo lỗi thì không xác nhận nhầm CV còn khớp', async () => {
  const cache = client();
  const first = { id: 90, cv_id: 1, match_score: 50, cv_match_status: 'current' };
  const observer = new QueryObserver(cache, {
    queryKey: historyKey, queryFn: async () => { throw new Error('Network unavailable'); },
  });
  let unsubscribe;
  try {
    cache.setQueryData(historyKey, [first]);
    unsubscribe = observer.subscribe(() => {});
    await syncCvSkillSaved(cache, 1, { skill_id: 10, source: 'manual' });
    assert.equal(observer.getCurrentResult().isError, true);
    assert.deepEqual(observer.getCurrentResult().data, [{ ...first, cv_match_status: 'unknown' }]);
  } finally { unsubscribe?.(); observer.destroy(); cache.clear(); }
});
