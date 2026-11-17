import type { CvMatchStatus } from '../types';
import { getCvMatchStatusInfo } from '../services/cvMatchStatus';

export default function CvMatchStatusBadge({ status, detailed = false }: {
  status: CvMatchStatus | undefined;
  detailed?: boolean;
}) {
  const info = getCvMatchStatusInfo(status);
  return (
    <div className={`cv-match-status-badge${detailed ? ' is-detailed' : ''}`}>
      <span className={`badge badge-${info.tone}`} title={info.description}>{info.label}</span>
      {detailed && <p>{info.description}</p>}
    </div>
  );
}
