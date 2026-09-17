from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class SkillGap(Base):
    __tablename__ = "skill_gaps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    cv_id = Column(Integer, ForeignKey("cvs.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)

    match_score = Column(Float, nullable=False)  # 0-100
    matched_skills = Column(JSON)   # [{"skill_id": 1, "skill_name": "Python", ...}]
    missing_skills = Column(JSON)   # [{"skill_id": 2, "skill_name": "Docker", "priority": "high", ...}]
    weak_skills = Column(JSON)      # [{"skill_id": 3, "skill_name": "SQL", "current_level": "beginner", ...}]
    ai_recommendation = Column(Text)  # AI-generated recommendation text

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="skill_gaps")
    cv = relationship("CV", back_populates="skill_gaps")
    job = relationship("Job", back_populates="skill_gaps")
