from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Auth Schemas ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: str = Field(default="ANALYST", description="ANALYST or ADMIN")

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    role: str
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    email: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None


# --- Company & Risk Profile Schemas ---
class CompanyCreate(BaseModel):
    name: str
    ticker: str
    industry: str
    financial_summary: Optional[Dict[str, Any]] = None

class CompanyOut(BaseModel):
    id: int
    name: str
    ticker: str
    industry: str
    financial_summary: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

class RiskProfileCreate(BaseModel):
    company_id: int
    overall_score: float
    risk_rating: str
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    interest_coverage: Optional[float] = None
    altman_z_score: Optional[float] = None

class RiskProfileOut(BaseModel):
    id: int
    company_id: int
    overall_score: float
    risk_rating: str
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    interest_coverage: Optional[float] = None
    altman_z_score: Optional[float] = None
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Regulatory References Schemas ---
class RegulatoryReferenceCreate(BaseModel):
    source: str
    section: str
    content: str

class RegulatoryReferenceOut(BaseModel):
    id: int
    source: str
    section: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Assessment History Schemas ---
class AssessmentRequest(BaseModel):
    company_id: Optional[int] = None
    query: str
    prompt_variant: str = Field(default="COT", description="ZERO_SHOT, FEW_SHOT, or COT")

class AssessmentOut(BaseModel):
    id: int
    company_id: Optional[int] = None
    query: str
    prompt_variant: str
    assessment_text: str
    confidence_score: float
    sources: Optional[List[Dict[str, Any]]] = None
    judge_accuracy: Optional[float] = None
    judge_completeness: Optional[float] = None
    judge_regulatory_alignment: Optional[float] = None
    judge_feedback: Optional[str] = None
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- Prompt Comparison Schemas ---
class PromptCompareRequest(BaseModel):
    company_id: Optional[int] = None
    query: str

class PromptCompareResult(BaseModel):
    prompt_variant: str
    assessment_text: str
    confidence_score: float
    judge_accuracy: float
    judge_completeness: float
    judge_regulatory_alignment: float
    judge_feedback: str

class PromptCompareResponse(BaseModel):
    query: str
    results: List[PromptCompareResult]
