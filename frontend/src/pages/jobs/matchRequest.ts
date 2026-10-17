import type { SkillGapResult } from '../../types';

export interface MatchRequest {
  readonly requestId: number;
  readonly jobId: number;
  readonly cvId: number;
}

export interface MatchOutcome {
  request: MatchRequest;
  result: SkillGapResult;
}

/** Mỗi lần đổi lựa chọn hoặc gửi lại sẽ vô hiệu hóa phản hồi trước đó. */
export function createMatchRequestTracker() {
  let sequence = 0;
  let active: MatchRequest | null = null;

  return {
    begin(jobId: number, cvId: number): MatchRequest {
      active = { requestId: ++sequence, jobId, cvId };
      return active;
    },
    invalidate() {
      active = null;
    },
    complete(request: MatchRequest): boolean {
      if (!active || active.requestId !== request.requestId ||
          active.jobId !== request.jobId || active.cvId !== request.cvId) return false;
      active = null;
      return true;
    },
  };
}

/** Chỉ hiển thị kết quả thuộc đúng lựa chọn đang có hiệu lực. */
export function getVisibleMatchResult(
  outcome: MatchOutcome | null,
  jobId: number | undefined,
  cvId: number | '',
): SkillGapResult | null {
  if (!outcome || outcome.request.jobId !== jobId || outcome.request.cvId !== cvId ||
      outcome.result.job.id !== jobId || outcome.result.cv_id !== cvId) return null;
  return outcome.result;
}

/** Lấy bản đã lưu đang được dùng chung với Báo cáo và Dashboard. */
export function getRecordedMatchResult(
  outcome: MatchOutcome | null,
  jobId: number | undefined,
  cvId: number | '',
  history: SkillGapResult[] | undefined,
): SkillGapResult | null {
  if (!outcome || !getVisibleMatchResult(outcome, jobId, cvId)) return null;
  const recorded = history?.find((result) => result.id === outcome.result.id);
  return recorded ? getVisibleMatchResult({ request: outcome.request, result: recorded }, jobId, cvId) : null;
}
