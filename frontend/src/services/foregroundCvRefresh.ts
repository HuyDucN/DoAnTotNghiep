import { focusManager } from '@tanstack/react-query';
import type { QueryClient } from '@tanstack/react-query';
import type { SkillGapResult } from '../types';

export const cvFocusQueryScopes = [
  ['cvs', 'mine'],
  ['cv-skills'],
  ['cv-status'],
  ['skill-gaps', 'mine'],
] as const;

/** Đọc lại dữ liệu CV khi trở lại tab, kể cả cache chưa hết 30 giây. */
export function createCvForegroundRefresh(client: QueryClient) {
  let disposed = false;
  let revision = 0;

  const refresh = async () => {
    if (disposed) return;
    const attempt = ++revision;
    await Promise.all(cvFocusQueryScopes.map((queryKey) => client.cancelQueries({ queryKey })));
    if (disposed || attempt !== revision) return;

    client.setQueryData<SkillGapResult[]>(['skill-gaps', 'mine'], (previous) =>
      previous?.map((gap) => ({ ...gap, cv_match_status: 'unknown' })));
    await Promise.all(cvFocusQueryScopes.map((queryKey) =>
      queryKey[0] === 'cv-status'
        ? client.resetQueries({ queryKey })
        : client.invalidateQueries({ queryKey })));
  };

  const unsubscribe = focusManager.subscribe((focused) => {
    if (focused) void refresh();
  });

  return {
    refresh,
    dispose() {
      disposed = true;
      revision++;
      unsubscribe();
    },
  };
}
