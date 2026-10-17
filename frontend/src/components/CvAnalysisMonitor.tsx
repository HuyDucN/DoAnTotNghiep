import { useEffect } from 'react';
import { useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import { cvApi } from '../services/api';
import { cvCompletionKey, cvStatusKey, myCvsKey, refreshCompletedCvs } from '../services/cvCache';
import type { CV, CVStatus } from '../types';

/** Keep lightweight status polling alive while navigating between private pages. */
export default function CvAnalysisMonitor() {
  const client = useQueryClient();
  const cvs = useQuery<CV[]>({ queryKey: myCvsKey, queryFn: () => cvApi.list() });
  const pending = (cvs.data ?? []).filter((cv) => cv.status === 'uploaded' || cv.status === 'processing');
  const statuses = useQueries({
    queries: pending.map((cv) => ({
      queryKey: cvStatusKey(cv.id),
      queryFn: () => cvApi.status(cv.id) as Promise<CVStatus>,
      refetchInterval: 3000,
      refetchOnMount: 'always' as const,
    })),
  });
  const completion = cvCompletionKey(cvs.dataUpdatedAt, statuses);
  useEffect(() => {
    if (!completion) return;
    const ids = completion.split('|').map((entry) => Number(entry.split(':')[0]));
    void refreshCompletedCvs(client, ids);
  }, [client, completion]);
  return null;
}
