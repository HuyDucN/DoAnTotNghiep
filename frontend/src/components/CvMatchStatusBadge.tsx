import type { CvMatchStatus } from '../types';
import { getCvMatchStatusInfo } from '../services/cvMatchStatus';

export default function CvMatchStatusBadge({ status, detailed = false }: {
  status: CvMatchStatus | undefined;
  detailed?: boolean;
}) {
  const info = getCvMatchStatusInfo(status);
  return (
    <div className="mt-1">
      <span className={`badge badge-${info.tone}`} title={info.description}>{info.label}</span>
      {detailed && <p className="text-muted text-xs mt-1">{info.description}</p>}
    </div>
  );
}
