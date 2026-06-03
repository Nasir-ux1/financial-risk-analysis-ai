import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from backend.app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="ANALYST", nullable=False)  # ANALYST or ADMIN
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    assessments = relationship("AssessmentHistory", back_populates="creator")


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    ticker = Column(String, index=True, nullable=False)
    industry = Column(String, nullable=False)
    financial_summary = Column(JSON, nullable=True)  # Stores basic balance sheet, income stmt values
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    risk_profiles = relationship("RiskProfile", back_populates="company", cascade="all, delete-orphan")
    assessments = relationship("AssessmentHistory", back_populates="company", cascade="all, delete-orphan")


class RiskProfile(Base):
    __tablename__ = "risk_profiles"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    overall_score = Column(Float, nullable=False)  # 0 to 100
    risk_rating = Column(String, nullable=False)  # LOW, MEDIUM, HIGH
    debt_to_equity = Column(Float, nullable=True)
    current_ratio = Column(Float, nullable=True)
    interest_coverage = Column(Float, nullable=True)
    altman_z_score = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="risk_profiles")


class RegulatoryReference(Base):
    __tablename__ = "regulatory_references"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, index=True, nullable=False)  # BASEL_III, IFRS_9, SEC, etc.
    section = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class AssessmentHistory(Base):
    __tablename__ = "assessment_history"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True)
    query = Column(Text, nullable=False)
    prompt_variant = Column(String, nullable=False)  # ZERO_SHOT, FEW_SHOT, COT
    assessment_text = Column(Text, nullable=False)
    confidence_score = Column(Float, default=0.0)  # 0.0 to 1.0
    sources = Column(JSON, nullable=True)  # List of dicts: [{"source": "...", "section": "..."}]
    
    # LLM-as-a-Judge evaluation metrics
    judge_accuracy = Column(Float, nullable=True)  # 0.0 to 1.0
    judge_completeness = Column(Float, nullable=True)  # 0.0 to 1.0
    judge_regulatory_alignment = Column(Float, nullable=True)  # 0.0 to 1.0
    judge_feedback = Column(Text, nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="assessments")
    creator = relationship("User", back_populates="assessments")
