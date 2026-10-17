import { CanceledError, isAxiosError } from 'axios';
import type { AxiosInstance, InternalAxiosRequestConfig } from 'axios';

declare module 'axios' {
  interface AxiosRequestConfig {
    authSessionVersion?: number;
    authSessionAuthenticated?: boolean;
  }
}

export interface AuthSessionSnapshot {
  version: number;
  token: string | null;
}

/** Yêu cầu và phản hồi chỉ có hiệu lực trong phiên đã khởi tạo chúng. */
export function attachSessionInterceptors(
  client: AxiosInstance,
  getSession: () => AuthSessionSnapshot,
  onUnauthorized: () => void,
) {
  const belongsToCurrentSession = (config: InternalAxiosRequestConfig | undefined) =>
    config?.authSessionVersion === getSession().version;

  client.interceptors.request.use((config) => {
    const session = getSession();
    config.authSessionVersion = session.version;
    config.authSessionAuthenticated = Boolean(session.token);
    if (session.token) config.headers.set('Authorization', `Bearer ${session.token}`);
    else config.headers.delete('Authorization');
    return config;
  }, undefined, { synchronous: true });

  client.interceptors.response.use(
    (response) => {
      if (!belongsToCurrentSession(response.config)) {
        throw new CanceledError('Phiên đăng nhập đã thay đổi.', response.config);
      }
      return response;
    },
    (error: unknown) => {
      if (isAxiosError(error) && error.config) {
        if (!belongsToCurrentSession(error.config)) {
          return Promise.reject(new CanceledError('Phiên đăng nhập đã thay đổi.', error.config));
        }
        // Lỗi đăng nhập ẩn danh được hiển thị tại form; không đăng xuất phiên khác.
        const authFormRequest = /\/auth\/(?:login|register|forgot-password|reset-password)(?:[?#]|$)/.test(error.config.url ?? '');
        if (error.response?.status === 401 && error.config.authSessionAuthenticated && !authFormRequest) {
          onUnauthorized();
        }
      }
      return Promise.reject(error);
    },
  );
}
