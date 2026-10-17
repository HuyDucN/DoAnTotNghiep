import type { CvMatchStatus } from '../types';

interface CvMatchStatusInfo {
  label: string;
  description: string;
  tone: 'success' | 'warning' | 'danger' | 'neutral';
}

const messages: Record<CvMatchStatus, CvMatchStatusInfo> = {
  current: {
    label: 'Đã đối chiếu với CV hiện tại',
    description: 'Dữ liệu CV dùng cho kết quả này vẫn khớp với CV hiện tại. Yêu cầu công việc được hiển thị theo nguồn ghi trong báo cáo.',
    tone: 'success',
  },
  changed: {
    label: 'CV đã thay đổi',
    description: 'Điểm này dùng dữ liệu CV trước khi thay đổi. Hãy so khớp lại để cập nhật.',
    tone: 'warning',
  },
  processing: {
    label: 'CV đang phân tích',
    description: 'Đây là kết quả đã lưu trước lần phân tích đang chạy. Chờ phân tích hoàn tất rồi so khớp lại.',
    tone: 'warning',
  },
  failed: {
    label: 'Phân tích CV thất bại',
    description: 'Điểm đã lưu chưa được xác nhận với CV hiện tại. Phân tích lại CV thành công rồi so khớp lại.',
    tone: 'danger',
  },
  unknown: {
    label: 'Chưa đối chiếu được CV',
    description: 'Chưa đủ thông tin để xác nhận kết quả này với CV hiện tại. Hãy so khớp lại để xác nhận.',
    tone: 'neutral',
  },
};

export function getCvMatchStatusInfo(status: CvMatchStatus | undefined): CvMatchStatusInfo {
  return status && Object.hasOwn(messages, status) ? messages[status] : messages.unknown;
}
