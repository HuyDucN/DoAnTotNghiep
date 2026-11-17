import type { UseQueryResult } from '@tanstack/react-query';
import { AlertCircle, Loader2, RefreshCw } from 'lucide-react';
import { getApiErrorMessage } from '../services/api';

export default function QueryLoadNotice({ query, label }: {
  query: Pick<UseQueryResult, 'data' | 'error' | 'isError' | 'isFetching' | 'refetch'>;
  label: string;
}) {
  if (query.isError) {
    return (
      <div className="query-load-notice" role="alert">
        <div className="query-load-icon"><AlertCircle size={17} aria-hidden="true" /></div>
        <div className="query-load-copy">
          <strong>Không thể tải {label}</strong>
          <p>
          {getApiErrorMessage(query.error, 'Vui lòng thử lại.')}
            {query.data !== undefined && ' Dữ liệu cũ vẫn đang được hiển thị; thay đổi mới chưa được xác nhận.'}
          </p>
        </div>
        <button className="btn btn-outline btn-sm query-load-action" disabled={query.isFetching}
          onClick={() => void query.refetch()}>
          {query.isFetching ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
          {query.isFetching ? 'Đang tải lại' : 'Thử lại'}
        </button>
      </div>
    );
  }
  if (query.isFetching && query.data !== undefined) {
    return <div className="query-refreshing" role="status">
      <Loader2 size={13} className="animate-spin" /> <span>Đang cập nhật {label}...</span>
    </div>;
  }
  return null;
}
