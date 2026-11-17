"""Ghi nhat ky kiem toan; caller tu commit."""
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def log_audit(
    db: Session,
    actor_id: Optional[int],
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    detail: Optional[dict[str, Any]] = None,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
    )
    db.add(entry)
    db.flush()
    return entry
