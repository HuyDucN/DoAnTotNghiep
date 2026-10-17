import { useEffect, useMemo } from 'react';
import type { ReactNode } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { useAuthStore } from '../store/authStore';
import { createSessionQueryClient } from '../services/sessionQueryClient';
import { createCvForegroundRefresh } from '../services/foregroundCvRefresh.ts';

export default function SessionQueryProvider({ children }: { children: ReactNode }) {
  const userId = useAuthStore((state) => state.user?.id);
  const sessionVersion = useAuthStore((state) => state.sessionVersion);
  const sessionKey = `${userId ?? 'anonymous'}:${sessionVersion}`;
  const queryClient = useMemo(() => createSessionQueryClient(sessionKey), [sessionKey]);

  useEffect(() => {
    const foreground = createCvForegroundRefresh(queryClient);
    return () => {
      foreground.dispose();
      queryClient.clear();
    };
  }, [queryClient]);

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
