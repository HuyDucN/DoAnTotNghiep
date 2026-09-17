from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class CV(Base):
    __tablename__ = "cvs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)  # bytes
    status = Column(
        Enum("uploaded", "processing", "analyzed", "failed"),
        default="uploaded",
        nullable=False,
    )
    raw_text = Column(Text)  # extracted text
    ai_analysis = Column(JSON)  # full AI response JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="cvs")
    cv_skills = relationship("CVSkill", back_populates="cv", cascade="all, delete-orphan")
    skill_gaps = relationship("SkillGap", back_populates="cv", cascade="all, delete-orphan")
