from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class AuditLog(Base):
    """Nhat ky hanh dong quan tri: ai lam gi, len doi tuong nao, khi nao."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(64), nullable=False, index=True)
    target_type = Column(String(32), nullable=True)
    target_id = Column(Integer, nullable=True)
    detail = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    actor = relationship("User", foreign_keys=[actor_id])
