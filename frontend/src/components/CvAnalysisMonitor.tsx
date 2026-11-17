import { useEffect } from 'react';
import { useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Loader2, Sparkles } from 'lucide-react';
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
  if (pending.length === 0) return null;

  return (
    <div className="cv-analysis-live" role="status" aria-live="polite">
      <span className="cv-analysis-live-icon"><Loader2 size={14} className="animate-spin" aria-hidden="true" /></span>
      <span className="cv-analysis-live-copy">
        <strong>AI đang phân tích CV</strong>
        <small>{pending.length === 1 ? 'Kết quả sẽ xuất hiện sau ít phút.' : `${pending.length} CV đang được xử lý.`}</small>
      </span>
      <Link to="/cv" className="cv-analysis-live-link"><Sparkles size={13} aria-hidden="true" /> Xem CV</Link>
    </div>
  );
}
