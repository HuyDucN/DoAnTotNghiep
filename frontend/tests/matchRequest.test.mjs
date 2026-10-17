import assert from 'node:assert/strict';
import test from 'node:test';
import { createMatchRequestTracker, getVisibleMatchResult } from '../src/pages/jobs/matchRequest.ts';

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((ok, fail) => { resolve = ok; reject = fail; });
  return { promise, resolve, reject };
}

test('phản hồi đang được chọn được nhận đúng một lần', () => {
  const tracker = createMatchRequestTracker();
  const request = tracker.begin(1, 10);
  assert.equal(tracker.complete(request), true);
  assert.equal(tracker.complete(request), false);
});

test('đổi CV trong lúc chờ làm phản hồi cũ hết hiệu lực', async () => {
  const tracker = createMatchRequestTracker();
  const response = deferred();
  const request = tracker.begin(1, 10);
  const accepted = response.promise.then(() => tracker.complete(request));
  tracker.invalidate();
  response.resolve();
  assert.equal(await accepted, false);
});

test('đổi công việc rồi quay lại vẫn không nhận phản hồi của lần cũ', () => {
  const tracker = createMatchRequestTracker();
  const old = tracker.begin(1, 10);
  tracker.invalidate();
  tracker.invalidate();
  assert.equal(tracker.complete(old), false);
});

test('phản hồi cũ về sau không ghi đè yêu cầu mới cùng CV và công việc', async () => {
  const tracker = createMatchRequestTracker();
  const firstResponse = deferred();
  const secondResponse = deferred();
  const first = tracker.begin(1, 10);
  const firstAccepted = firstResponse.promise.then(() => tracker.complete(first));
  const second = tracker.begin(1, 10);
  const secondAccepted = secondResponse.promise.then(() => tracker.complete(second));
  secondResponse.resolve();
  assert.equal(await secondAccepted, true);
  firstResponse.resolve();
  assert.equal(await firstAccepted, false);
});

test('phản hồi cũ về trước không kết thúc yêu cầu mới', async () => {
  const tracker = createMatchRequestTracker();
  const firstResponse = deferred();
  const secondResponse = deferred();
  const first = tracker.begin(1, 10);
  const firstAccepted = firstResponse.promise.then(() => tracker.complete(first));
  const second = tracker.begin(2, 20);
  const secondAccepted = secondResponse.promise.then(() => tracker.complete(second));
  firstResponse.resolve();
  assert.equal(await firstAccepted, false);
  secondResponse.resolve();
  assert.equal(await secondAccepted, true);
});

test('lỗi của yêu cầu cũ không kết thúc yêu cầu mới', async () => {
  const tracker = createMatchRequestTracker();
  const failedResponse = deferred();
  const old = tracker.begin(1, 10);
  const failureAccepted = failedResponse.promise.catch(() => tracker.complete(old));
  const current = tracker.begin(2, 20);
  failedResponse.reject(new Error('lỗi mô phỏng'));
  assert.equal(await failureAccepted, false);
  assert.equal(tracker.complete(current), true);
});

test('rời trang làm phản hồi đang chờ hết hiệu lực', () => {
  const tracker = createMatchRequestTracker();
  const request = tracker.begin(1, 10);
  tracker.invalidate();
  assert.equal(tracker.complete(request), false);
});

test('kết quả chỉ hiện cho đúng cặp CV và công việc', () => {
  const outcome = {
    request: { requestId: 1, jobId: 1, cvId: 10 },
    result: { cv_id: 10, cv_filename: 'cv.pdf', job: { id: 1 }, match_score: 83.3 },
  };
  assert.equal(getVisibleMatchResult(outcome, 1, 10), outcome.result);
  assert.equal(getVisibleMatchResult(outcome, 2, 10), null);
  assert.equal(getVisibleMatchResult(outcome, 1, 20), null);
  assert.equal(getVisibleMatchResult(outcome, undefined, 10), null);
  assert.equal(getVisibleMatchResult(outcome, 1, ''), null);
  assert.equal(getVisibleMatchResult(null, 1, 10), null);
});

test('kết quả trả sai công việc không được gắn vào lựa chọn hiện tại', () => {
  const outcome = {
    request: { requestId: 1, jobId: 1, cvId: 10 },
    result: { cv_id: 10, cv_filename: 'cv.pdf', job: { id: 2 }, match_score: 90 },
  };
  assert.equal(getVisibleMatchResult(outcome, 1, 10), null);
});

test('phản hồi sai CV không làm mất quyền nhận phản hồi đúng', () => {
  const tracker = createMatchRequestTracker();
  const request = tracker.begin(1, 10);
  assert.equal(tracker.complete({ ...request, cvId: 20 }), false);
  assert.equal(tracker.complete(request), true);
});

test('phản hồi cùng công việc nhưng sai mã CV bị từ chối dù trùng tên file', () => {
  const request = { requestId: 1, jobId: 1, cvId: 10 };
  const wrong = { request, result: { cv_id: 20, cv_filename: 'cv.pdf', job: { id: 1 } } };
  const correct = { request, result: { cv_id: 10, cv_filename: 'cv.pdf', job: { id: 1 } } };
  assert.equal(getVisibleMatchResult(wrong, 1, 10), null);
  assert.equal(getVisibleMatchResult(correct, 1, 10), correct.result);
});

test('phản hồi thiếu mã CV không được đoán là CV đang chọn', () => {
  const outcome = {
    request: { requestId: 1, jobId: 1, cvId: 10 },
    result: { cv_filename: 'cv.pdf', job: { id: 1 } },
  };
  assert.equal(getVisibleMatchResult(outcome, 1, 10), null);
});
