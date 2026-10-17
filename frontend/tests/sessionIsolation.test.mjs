import assert from 'node:assert/strict';
import test, { beforeEach } from 'node:test';
import axios, { AxiosError, isCancel } from 'axios';
import { isCancelledError } from '@tanstack/react-query';
import { createSessionQueryClient } from '../src/services/sessionQueryClient.ts';
import { attachSessionInterceptors } from '../src/services/sessionInterceptors.ts';

class MemoryStorage {
  values = new Map();
  getItem(key) { return this.values.get(key) ?? null; }
  setItem(key, value) { this.values.set(key, String(value)); }
  removeItem(key) { this.values.delete(key); }
  clear() { this.values.clear(); }
}

const storage = new MemoryStorage();
Object.defineProperty(globalThis, 'localStorage', { value: storage, configurable: true });
Object.defineProperty(globalThis, 'window', { value: { localStorage: storage }, configurable: true });
const { useAuthStore } = await import('../src/store/authStore.ts');

function user(id, role = 'user') {
  return { id, role, email: `user${id}@example.test`, full_name: `User ${id}`, is_active: true, created_at: '2026-10-01' };
}

beforeEach(() => {
  storage.clear();
  useAuthStore.setState({ user: null, token: null, isAuthenticated: false, sessionVersion: 0 });
});

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((ok, fail) => { resolve = ok; reject = fail; });
  return { promise, resolve, reject };
}

function apiFixture() {
  const requests = [];
  const expired = [];
  const client = axios.create({ adapter: (config) => {
    const network = deferred();
    const response = (status, data) => ({ config, status, data, statusText: String(status), headers: {} });
    requests.push({
      config,
      succeed: (data = { ok: true }) => network.resolve(response(200, data)),
      unauthorized: () => network.reject(new AxiosError('Unauthorized', 'ERR_BAD_REQUEST', config, null, response(401, {}))),
      failHttp: (status, data) => network.reject(new AxiosError('Request failed', 'ERR_BAD_REQUEST', config, null, response(status, data))),
      failNetwork: () => network.reject(new AxiosError('Network Error', 'ERR_NETWORK', config)),
    });
    return network.promise;
  } });
  attachSessionInterceptors(client, () => {
    const state = useAuthStore.getState();
    return { version: state.sessionVersion, token: state.token };
  }, () => {
    expired.push(useAuthStore.getState().sessionVersion);
    useAuthStore.getState().logout();
  });
  return { client, requests, expired };
}

test('đăng xuất rồi đăng nhập lại cùng JWT vẫn tạo phiên khác', () => {
  useAuthStore.getState().setAuth(user(1), 'same-token');
  const first = useAuthStore.getState().sessionVersion;
  useAuthStore.getState().logout();
  useAuthStore.getState().setAuth(user(1), 'same-token');
  assert.ok(useAuthStore.getState().sessionVersion > first);
  assert.equal(useAuthStore.getState().token, 'same-token');
});

test('cập nhật tên không đặt lại cache phiên đang dùng', () => {
  useAuthStore.getState().setAuth(user(1), 'token-a');
  const version = useAuthStore.getState().sessionVersion;
  useAuthStore.getState().updateUser({ full_name: 'New Name' });
  assert.equal(useAuthStore.getState().sessionVersion, version);
  assert.equal(useAuthStore.getState().user.full_name, 'New Name');
});

test('đổi tài khoản hoặc quyền tạo phiên mới dù token trùng nhau', () => {
  useAuthStore.getState().setAuth(user(1), 'token');
  const first = useAuthStore.getState().sessionVersion;
  useAuthStore.getState().setAuth(user(2), 'token');
  const second = useAuthStore.getState().sessionVersion;
  useAuthStore.getState().setAuth(user(2, 'admin'), 'token');
  assert.ok(second > first);
  assert.ok(useAuthStore.getState().sessionVersion > second);
});

test('đăng xuất xóa token và dữ liệu người dùng đã lưu', () => {
  useAuthStore.getState().setAuth(user(1), 'token-a');
  storage.setItem('user', 'legacy-user');
  useAuthStore.getState().logout();
  assert.equal(storage.getItem('token'), null);
  assert.equal(storage.getItem('user'), null);
  const saved = JSON.parse(storage.getItem('auth-store')).state;
  assert.equal(saved.user, null);
  assert.equal(saved.token, null);
  assert.equal(saved.isAuthenticated, false);
});

test('cache CV, báo cáo và quản trị không được dùng chung giữa hai phiên', () => {
  const first = createSessionQueryClient('1:1');
  const second = createSessionQueryClient('2:3');
  const keys = [['cvs', 'mine'], ['skill-gaps', 'mine'], ['admin', 'users']];
  try {
    for (const key of keys) first.setQueryData(key, [{ owner: 1, private: true }]);
    for (const key of keys) assert.equal(second.getQueryData(key), undefined);
    second.setQueryData(['cvs', 'mine'], [{ owner: 2 }]);
    first.clear();
    assert.deepEqual(second.getQueryData(['cvs', 'mine']), [{ owner: 2 }]);
    assert.equal(first.getQueryCache().getAll().length, 0);
  } finally {
    first.clear();
    second.clear();
  }
});

test('truy vấn cũ về muộn không khôi phục cache đã xóa hoặc ghi đè phiên mới', async () => {
  const first = createSessionQueryClient('1:1');
  const second = createSessionQueryClient('2:3');
  const network = deferred();
  try {
    const old = first.fetchQuery({ queryKey: ['cvs', 'mine'], queryFn: () => network.promise });
    const canceled = assert.rejects(old, (error) => isCancelledError(error));
    first.clear();
    await canceled;
    await second.fetchQuery({ queryKey: ['cvs', 'mine'], queryFn: async () => [{ owner: 2 }] });
    network.resolve([{ owner: 1 }]);
    await new Promise((resolve) => setImmediate(resolve));
    assert.equal(first.getQueryData(['cvs', 'mine']), undefined);
    assert.deepEqual(second.getQueryData(['cvs', 'mine']), [{ owner: 2 }]);
  } finally {
    first.clear();
    second.clear();
  }
});

test('request chốt token ngay khi gửi, không lấy token của tài khoản đăng nhập sau', async () => {
  const { client, requests } = apiFixture();
  useAuthStore.getState().setAuth(user(1), 'token-a');
  const first = client.get('/cv/list');
  const canceled = assert.rejects(first, (error) => isCancel(error));
  useAuthStore.getState().setAuth(user(2), 'token-b');
  const second = client.get('/cv/list');
  assert.equal(requests[0].config.headers.get('Authorization'), 'Bearer token-a');
  assert.equal(requests[1].config.headers.get('Authorization'), 'Bearer token-b');
  requests[0].succeed({ owner: 1 });
  requests[1].succeed({ owner: 2 });
  await canceled;
  assert.deepEqual((await second).data, { owner: 2 });
});

test('401 của tài khoản cũ không đăng xuất tài khoản mới', async () => {
  const { client, requests, expired } = apiFixture();
  useAuthStore.getState().setAuth(user(1), 'token-a');
  const old = client.get('/users/me');
  const canceled = assert.rejects(old, (error) => isCancel(error));
  useAuthStore.getState().logout();
  useAuthStore.getState().setAuth(user(2), 'token-b');
  requests[0].unauthorized();
  await canceled;
  assert.deepEqual(expired, []);
  assert.equal(useAuthStore.getState().user.id, 2);
  assert.equal(useAuthStore.getState().isAuthenticated, true);
});

test('401 của JWT cũ không làm mất JWT mới của cùng người dùng', async () => {
  const { client, requests, expired } = apiFixture();
  useAuthStore.getState().setAuth(user(1), 'old-token');
  const old = client.get('/users/me');
  const canceled = assert.rejects(old, (error) => isCancel(error));
  useAuthStore.getState().setAuth(user(1), 'new-token');
  requests[0].unauthorized();
  await canceled;
  assert.deepEqual(expired, []);
  assert.equal(useAuthStore.getState().token, 'new-token');
});

test('phản hồi từ lần đăng nhập trước bị chặn dù người dùng và JWT giống hệt', async () => {
  const { client, requests } = apiFixture();
  useAuthStore.getState().setAuth(user(1), 'same-token');
  const request = client.get('/cv/list');
  const canceled = assert.rejects(request, (error) => isCancel(error));
  useAuthStore.getState().logout();
  useAuthStore.getState().setAuth(user(1), 'same-token');
  requests[0].succeed({ private: 'old session' });
  await canceled;
  assert.equal(useAuthStore.getState().isAuthenticated, true);
});

test('phản hồi thành công sau đăng xuất bị hủy trước khi đưa dữ liệu vào trang', async () => {
  const { client, requests } = apiFixture();
  useAuthStore.getState().setAuth(user(1), 'token-a');
  const old = client.get('/cv/1/file');
  const canceled = assert.rejects(old, (error) => isCancel(error));
  useAuthStore.getState().logout();
  requests[0].succeed('private file');
  await canceled;
});

test('401 của phiên hiện tại vẫn kết thúc phiên đúng cách', async () => {
  const { client, requests, expired } = apiFixture();
  useAuthStore.getState().setAuth(user(1), 'expired-token');
  const request = client.get('/users/me');
  const rejected = assert.rejects(request, (error) => error.response?.status === 401);
  requests[0].unauthorized();
  await rejected;
  assert.equal(expired.length, 1);
  assert.equal(useAuthStore.getState().isAuthenticated, false);
  assert.equal(storage.getItem('token'), null);
});

test('đăng nhập sai khi ẩn danh không kích hoạt đăng xuất toàn cục', async () => {
  const { client, requests, expired } = apiFixture();
  const request = client.post('/auth/login', { email: 'wrong@example.test', password: 'wrong' });
  const rejected = assert.rejects(request, (error) => error.response?.status === 401);
  requests[0].unauthorized();
  await rejected;
  assert.deepEqual(expired, []);
  assert.equal(requests[0].config.headers.has('Authorization'), false);
});

test('đăng nhập sai tài khoản khác không làm mất phiên đang hoạt động', async () => {
  const { client, requests, expired } = apiFixture();
  useAuthStore.getState().setAuth(user(1), 'token-a');
  const request = client.post('/auth/login', { email: 'wrong@example.test', password: 'wrong' });
  const rejected = assert.rejects(request, (error) => error.response?.status === 401);
  requests[0].unauthorized();
  await rejected;
  assert.deepEqual(expired, []);
  assert.equal(useAuthStore.getState().token, 'token-a');
});

test('lỗi mạng của phiên hiện tại được trả nguyên trạng, không đăng xuất', async () => {
  const { client, requests, expired } = apiFixture();
  useAuthStore.getState().setAuth(user(1), 'token-a');
  const request = client.get('/cv/list');
  const rejected = assert.rejects(request, (error) => error.code === 'ERR_NETWORK');
  requests[0].failNetwork();
  await rejected;
  assert.deepEqual(expired, []);
  assert.equal(useAuthStore.getState().isAuthenticated, true);
});

test('đổi mật khẩu thành công kết thúc đúng phiên và xóa token đã lưu', async () => {
  const { client, requests } = apiFixture();
  useAuthStore.getState().setAuth(user(1), 'old-token');
  const session = useAuthStore.getState();
  const request = client.put('/users/me/password', { old_password: 'old', new_password: 'new' });
  requests[0].succeed({ message: 'Đổi mật khẩu thành công' });
  await request;
  assert.equal(useAuthStore.getState().logoutIfCurrentSession(session.sessionVersion, session.user.id), true);
  assert.equal(useAuthStore.getState().isAuthenticated, false);
  assert.equal(storage.getItem('token'), null);
  assert.equal(JSON.parse(storage.getItem('auth-store')).state.token, null);
});

test('phản hồi đổi mật khẩu về muộn không đăng xuất tài khoản mới', async () => {
  const { client, requests } = apiFixture();
  useAuthStore.getState().setAuth(user(1), 'old-token');
  const session = useAuthStore.getState();
  const request = client.put('/users/me/password', {});
  const canceled = assert.rejects(request, (error) => isCancel(error));
  useAuthStore.getState().setAuth(user(2), 'other-token');
  requests[0].succeed();
  await canceled;
  assert.equal(useAuthStore.getState().logoutIfCurrentSession(session.sessionVersion, 1), false);
  assert.equal(useAuthStore.getState().user.id, 2);
  assert.equal(storage.getItem('token'), 'other-token');
});

test('đăng nhập lại cùng tài khoản được bảo vệ khỏi thao tác kết thúc phiên cũ', () => {
  useAuthStore.getState().setAuth(user(1), 'old-token');
  const session = useAuthStore.getState();
  useAuthStore.getState().logout();
  useAuthStore.getState().setAuth(user(1), 'new-token');
  assert.equal(useAuthStore.getState().logoutIfCurrentSession(session.sessionVersion, 1), false);
  assert.equal(useAuthStore.getState().token, 'new-token');
});

test('đặt lại mật khẩu chỉ kết thúc phiên của tài khoản trong phản hồi', () => {
  useAuthStore.getState().setAuth(user(1), 'token-a');
  const version = useAuthStore.getState().sessionVersion;
  assert.equal(useAuthStore.getState().logoutIfCurrentSession(version, 2), false);
  assert.equal(useAuthStore.getState().token, 'token-a');
  assert.equal(useAuthStore.getState().logoutIfCurrentSession(version, 1), true);
  assert.equal(useAuthStore.getState().token, null);
});

test('khôi phục khi ẩn danh không tạo thêm lần đăng xuất', () => {
  const version = useAuthStore.getState().sessionVersion;
  assert.equal(useAuthStore.getState().logoutIfCurrentSession(version, 1), false);
  assert.equal(useAuthStore.getState().sessionVersion, version);
});

test('lỗi đổi mật khẩu giữ phiên hiện tại để người dùng sửa thông tin', async () => {
  const { client, requests, expired } = apiFixture();
  useAuthStore.getState().setAuth(user(1), 'token-a');
  const request = client.put('/users/me/password', {});
  const rejected = assert.rejects(request, (error) => error.code === 'ERR_NETWORK');
  requests[0].failNetwork();
  await rejected;
  assert.deepEqual(expired, []);
  assert.equal(useAuthStore.getState().token, 'token-a');
});

test('tài khoản bị khóa xóa phiên khi API trả 401 và chỉ xử lý một lần cho nhiều request', async () => {
  const { client, requests, expired } = apiFixture();
  useAuthStore.getState().setAuth(user(1), 'locked-token');
  const first = client.get('/users/me/account');
  const second = client.get('/cv/list');
  const rejected = assert.rejects(first, (error) => error.response?.status === 401);
  const canceled = assert.rejects(second, (error) => isCancel(error));
  const data = { detail: 'Tài khoản đã bị khóa. Vui lòng liên hệ quản trị viên.' };
  requests[0].failHttp(401, data);
  await rejected;
  requests[1].failHttp(401, data);
  await canceled;
  assert.equal(expired.length, 1);
  assert.equal(useAuthStore.getState().isAuthenticated, false);
  assert.equal(useAuthStore.getState().user, null);
  assert.equal(storage.getItem('token'), null);
  assert.equal(JSON.parse(storage.getItem('auth-store')).state.token, null);
});

test('phản hồi khóa tài khoản cũ không kết thúc phiên vừa đăng nhập', async () => {
  const { client, requests, expired } = apiFixture();
  useAuthStore.getState().setAuth(user(1), 'locked-token');
  const first = client.get('/users/me');
  const canceled = assert.rejects(first, (error) => isCancel(error));
  useAuthStore.getState().setAuth(user(2), 'new-token');
  requests[0].failHttp(401, { detail: 'Tài khoản đã bị khóa.' });
  await canceled;
  assert.deepEqual(expired, []);
  assert.equal(useAuthStore.getState().token, 'new-token');
  assert.equal(useAuthStore.getState().user.id, 2);
});

for (const status of [400, 403, 422]) {
  test(`lỗi ${status} của request được bảo vệ không đăng xuất tài khoản đang hoạt động`, async () => {
    const { client, requests, expired } = apiFixture();
    useAuthStore.getState().setAuth(user(1), 'active-token');
    const request = client.put('/users/me/account', {});
    const rejected = assert.rejects(request, (error) => error.response?.status === status);
    requests[0].failHttp(status, { detail: status === 403 ? 'Không có quyền admin' : 'Dữ liệu không hợp lệ' });
    await rejected;
    assert.deepEqual(expired, []);
    assert.equal(useAuthStore.getState().token, 'active-token');
  });
}

test('thử đăng nhập tài khoản bị khóa chỉ báo lỗi tại form, giữ phiên khác đang hoạt động', async () => {
  const { client, requests, expired } = apiFixture();
  useAuthStore.getState().setAuth(user(2), 'active-token');
  const request = client.post('/auth/login', { email: 'locked@example.test', password: 'password' });
  const rejected = assert.rejects(request, (error) => error.response?.data?.detail === 'Tài khoản đã bị khóa');
  requests[0].failHttp(400, { detail: 'Tài khoản đã bị khóa' });
  await rejected;
  assert.deepEqual(expired, []);
  assert.equal(useAuthStore.getState().token, 'active-token');
  assert.equal(useAuthStore.getState().user.id, 2);
});
