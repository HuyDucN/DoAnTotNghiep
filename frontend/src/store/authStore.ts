import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '../types';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  sessionVersion: number;
  setAuth: (user: User, token: string) => void;
  logout: () => void;
  logoutIfCurrentSession: (expectedVersion: number, userId: number) => boolean;
  updateUser: (user: Partial<User>) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      sessionVersion: 0,

      setAuth: (user, token) => {
        localStorage.setItem('token', token);
        set((state) => {
          const changed = !state.isAuthenticated || state.user?.id !== user.id ||
            state.user?.role !== user.role || state.token !== token;
          return { user, token, isAuthenticated: true, sessionVersion: state.sessionVersion + Number(changed) };
        });
      },

      logout: () => {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        set((state) => ({ user: null, token: null, isAuthenticated: false, sessionVersion: state.sessionVersion + 1 }));
      },

      logoutIfCurrentSession: (expectedVersion, userId) => {
        const state = get();
        if (!state.isAuthenticated || state.sessionVersion !== expectedVersion || state.user?.id !== userId) {
          return false;
        }
        state.logout();
        return true;
      },

      updateUser: (partial) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...partial } : null,
        })),
    }),
    {
      name: 'auth-store',
      partialize: (state) => ({ user: state.user, token: state.token, isAuthenticated: state.isAuthenticated }),
    }
  )
);
