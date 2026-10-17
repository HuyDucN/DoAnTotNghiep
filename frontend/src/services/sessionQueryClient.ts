import { QueryClient } from '@tanstack/react-query';
import { cvFocusQueryScopes } from './foregroundCvRefresh.ts';

/** Mỗi phiên sở hữu cache riêng, kể cả khi query dùng cùng tên cvs/mine. */
export function createSessionQueryClient(sessionKey: string) {
  const client = new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: true,
        retry: 1,
        meta: { sessionKey },
      },
      mutations: { meta: { sessionKey } },
    },
  });
  for (const queryKey of cvFocusQueryScopes) {
    // Nhóm CV được làm mới có hủy lượt đọc cũ bởi foregroundCvRefresh.
    client.setQueryDefaults(queryKey, { refetchOnWindowFocus: false });
  }
  return client;
}
