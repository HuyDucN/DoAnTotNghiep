import type { QueryClient } from '@tanstack/react-query';
import type { CV, CVSkillItem, CVStatus, CvMatchStatus, SkillGapResult } from '../types';

export const myCvsKey = ['cvs', 'mine'] as const;
export const cvStatusKey = (cvId: number) => ['cv-status', cvId] as const;
export const cvSkillsKey = (cvId: number | null) => ['cv-skills', cvId] as const;
const historyKey = ['skill-gaps', 'mine'] as const;

function markCvHistory(client: QueryClient, cvIds: number[], status: CvMatchStatus) {
  const ids = new Set(cvIds);
  client.setQueryData<SkillGapResult[]>(historyKey, (previous) => previous?.map((gap) =>
    ids.has(gap.cv_id) ? { ...gap, cv_match_status: status } : gap));
}

/** Cancel earlier reads before inserting the server's accepted analysis attempt. */
export async function syncCvAnalysisStarted(client: QueryClient, cv: CV) {
  await Promise.all([
    client.cancelQueries({ queryKey: myCvsKey, exact: true }),
    client.cancelQueries({ queryKey: cvStatusKey(cv.id), exact: true }),
    client.cancelQueries({ queryKey: cvSkillsKey(cv.id), exact: true }),
    client.cancelQueries({ queryKey: historyKey, exact: true }),
  ]);
  client.setQueryData<CV[]>(myCvsKey, (previous) => {
    if (!previous) return undefined;
    return previous.some((item) => item.id === cv.id)
      ? previous.map((item) => item.id === cv.id ? cv : item)
      : [cv, ...previous];
  });
  client.setQueryData<CVStatus>(cvStatusKey(cv.id), { id: cv.id, status: cv.status });
  markCvHistory(client, [cv.id], 'processing');
  await Promise.all([
    client.invalidateQueries({ queryKey: myCvsKey, exact: true }),
    client.invalidateQueries({ queryKey: cvSkillsKey(cv.id), exact: true }),
    client.invalidateQueries({ queryKey: historyKey, exact: true }),
  ]);
}

export async function syncCvDeleted(client: QueryClient, cvId: number) {
  await Promise.all([
    client.cancelQueries({ queryKey: myCvsKey, exact: true }),
    client.cancelQueries({ queryKey: historyKey, exact: true }),
    client.cancelQueries({ queryKey: cvStatusKey(cvId), exact: true }),
    client.cancelQueries({ queryKey: cvSkillsKey(cvId), exact: true }),
  ]);
  client.setQueryData<CV[]>(myCvsKey, (previous) => previous?.filter((cv) => cv.id !== cvId));
  client.removeQueries({ queryKey: cvStatusKey(cvId), exact: true });
  client.removeQueries({ queryKey: cvSkillsKey(cvId), exact: true });
  await Promise.all([
    client.invalidateQueries({ queryKey: myCvsKey, exact: true }),
    // Reload history after the server cascades deletion to this CV's results.
    client.resetQueries({ queryKey: historyKey, exact: true }),
    client.invalidateQueries({ queryKey: ['admin', 'cvs'] }),
  ]);
}

export async function refreshCompletedCvs(client: QueryClient, cvIds: number[]) {
  if (cvIds.length === 0) return;
  const ids = [...new Set(cvIds)];
  await Promise.all([
    client.cancelQueries({ queryKey: myCvsKey, exact: true }),
    ...ids.map((id) => client.cancelQueries({ queryKey: cvSkillsKey(id), exact: true })),
    client.cancelQueries({ queryKey: historyKey, exact: true }),
  ]);
  markCvHistory(client, ids, 'unknown');
  await Promise.all([
    client.invalidateQueries({ queryKey: myCvsKey, exact: true }),
    ...ids.map((id) => client.invalidateQueries({ queryKey: cvSkillsKey(id), exact: true })),
    client.invalidateQueries({ queryKey: historyKey, exact: true }),
  ]);
}

export async function syncCvSkillSaved(client: QueryClient, cvId: number, saved: CVSkillItem) {
  const queryKey = cvSkillsKey(cvId);
  await Promise.all([
    client.cancelQueries({ queryKey, exact: true }),
    client.cancelQueries({ queryKey: historyKey, exact: true }),
  ]);
  client.setQueryData<CVSkillItem[]>(queryKey, (previous) => previous
    ? [...previous.filter((skill) => skill.skill_id !== saved.skill_id), saved]
    : undefined);
  markCvHistory(client, [cvId], 'unknown');
  await Promise.all([
    client.invalidateQueries({ queryKey, exact: true }),
    client.invalidateQueries({ queryKey: historyKey, exact: true }),
  ]);
}

export async function syncCvSkillDeleted(client: QueryClient, cvId: number, skillId: number) {
  const queryKey = cvSkillsKey(cvId);
  await Promise.all([
    client.cancelQueries({ queryKey, exact: true }),
    client.cancelQueries({ queryKey: historyKey, exact: true }),
  ]);
  client.setQueryData<CVSkillItem[]>(queryKey, (previous) => previous?.filter((skill) => skill.skill_id !== skillId));
  markCvHistory(client, [cvId], 'unknown');
  await Promise.all([
    client.invalidateQueries({ queryKey, exact: true }),
    client.invalidateQueries({ queryKey: historyKey, exact: true }),
  ]);
}

export function cvCompletionKey(
  listUpdatedAt: number,
  reads: { data?: CVStatus; dataUpdatedAt: number }[],
): string {
  return reads.flatMap(({ data, dataUpdatedAt }) =>
    data && dataUpdatedAt >= listUpdatedAt && (data.status === 'analyzed' || data.status === 'failed')
      ? [`${data.id}:${dataUpdatedAt}`] : [],
  ).join('|');
}
