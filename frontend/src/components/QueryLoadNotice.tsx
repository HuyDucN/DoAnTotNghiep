import type { UseQueryResult } from '@tanstack/react-query';
import { AlertCircle, Loader2, RefreshCw } from 'lucide-react';
import { getApiErrorMessage } from '../services/api';

export default function QueryLoadNotice({ query, label }: {
  query: Pick<UseQueryResult, 'data' | 'error' | 'isError' | 'isFetching' | 'refetch'>;
  label: string;
}) {
  if (query.isError) {
    return (
      <div className="card" role="alert" style={{ padding: '1rem' }}>
        <p className="text-warning flex items-center gap-2">
          <AlertCircle size={18} aria-hidden="true" /> Không thể tải {label}.
        </p>
        <p className="text-muted text-sm mt-1">
          {getApiErrorMessage(query.error, 'Vui lòng thử lại.')}
          {query.data !== undefined && ' Đang hiển thị dữ liệu đã tải trước đó; chưa xác nhận được thay đổi mới.'}
        </p>
        <button className="btn btn-outline btn-sm mt-3" disabled={query.isFetching}
          onClick={() => void query.refetch()}>
          {query.isFetching ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
          {query.isFetching ? 'Đang tải lại...' : `Thử tải lại ${label}`}
        </button>
      </div>
    );
  }
  if (query.isFetching && query.data !== undefined) {
    return <p className="text-muted text-sm flex items-center gap-2" role="status">
      <Loader2 size={14} className="animate-spin" /> Đang cập nhật {label}...
    </p>;
  }
  return null;
}
