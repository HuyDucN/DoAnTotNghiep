from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum, Float
from sqlalchemy.orm import relationship
from app.core.database import Base


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    normalized_name = Column(String(255), unique=True, nullable=False, index=True)
    category = Column(
        Enum(
            "programming_language",
            "framework",
            "database",
            "cloud",
            "devops",
            "ai_ml",
            "soft_skill",
            "tool",
            "other",
        ),
        default="other",
    )
    description = Column(Text)

    # Relationships
    cv_skills = relationship("CVSkill", back_populates="skill")
    job_skills = relationship("JobSkill", back_populates="skill")


class CVSkill(Base):
    __tablename__ = "cv_skills"

    id = Column(Integer, primary_key=True, index=True)
    cv_id = Column(Integer, ForeignKey("cvs.id", ondelete="CASCADE"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    proficiency_level = Column(
        Enum("beginner", "intermediate", "advanced", "expert"),
        default="intermediate",
    )
    years_experience = Column(Float, default=0)
    source = Column(String(50), default="ai_extracted")  # ai_extracted | manual

    # Relationships
    cv = relationship("CV", back_populates="cv_skills")
    skill = relationship("Skill", back_populates="cv_skills")
