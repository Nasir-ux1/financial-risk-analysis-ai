from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from backend.app.database import get_db
from backend.app.models import Company, RiskProfile
from backend.app.schemas import CompanyCreate, CompanyOut, RiskProfileOut
from backend.app.auth import require_analyst

router = APIRouter(prefix="/companies", tags=["Companies"])

def calculate_financial_ratios(company_id: int, summary: dict) -> RiskProfile:
    """
    Utility helper to compute critical risk indicators based on balance sheet & income statements.
    Includes current ratio, debt-to-equity, interest coverage, and Altman Z-Score.
    """
    # Extract values with fallbacks
    total_assets = summary.get("total_assets", 1.0) or 1.0
    total_liabilities = summary.get("total_liabilities", 0.0) or 0.0
    current_assets = summary.get("current_assets", 0.0) or 0.0
    current_liabilities = summary.get("current_liabilities", 1.0) or 1.0
    retained_earnings = summary.get("retained_earnings", 0.0) or 0.0
    ebit = summary.get("ebit", 0.0) or 0.0
    revenue = summary.get("revenue", 0.0) or 0.0
    equity = summary.get("market_equity", 1.0) or 1.0

    # Ratios
    current_ratio = round(current_assets / current_liabilities, 2)
    debt_to_equity = round(total_liabilities / equity, 2) if equity > 0 else 99.0
    
    # Interest coverage
    interest_expense = summary.get("interest_expense", 0.0) or 1.0
    interest_coverage = round(ebit / interest_expense, 2) if interest_expense > 0 else 99.0

    # Altman Z-Score calculation (for private/general non-manufacturers)
    # Z = 1.2A + 1.4B + 3.3C + 0.6D + 0.99E
    # A = Working Capital / Total Assets
    # B = Retained Earnings / Total Assets
    # C = EBIT / Total Assets
    # D = Market Value of Equity / Total Liabilities
    # E = Sales / Total Assets
    working_capital = current_assets - current_liabilities
    a = working_capital / total_assets
    b = retained_earnings / total_assets
    c = ebit / total_assets
    d = equity / total_liabilities if total_liabilities > 0 else 99.0
    e = revenue / total_assets
    
    altman_z = round(1.2 * a + 1.4 * b + 3.3 * c + 0.6 * d + 0.99 * e, 2)

    # Determine risk category
    score = 0.0
    if debt_to_equity > 2.0: score += 25
    elif debt_to_equity > 1.0: score += 10
    
    if current_ratio < 1.0: score += 25
    elif current_ratio < 1.5: score += 10
    
    if interest_coverage < 1.5: score += 25
    elif interest_coverage < 3.0: score += 10
    
    if altman_z < 1.8: score += 20
    elif altman_z < 3.0: score += 8
    
    score = min(max(score, 10.0), 95.0)
    
    if score >= 70.0:
        rating = "HIGH"
    elif score >= 40.0:
        rating = "MEDIUM"
    else:
        rating = "LOW"

    return RiskProfile(
        company_id=company_id,
        overall_score=score,
        risk_rating=rating,
        debt_to_equity=debt_to_equity,
        current_ratio=current_ratio,
        interest_coverage=interest_coverage,
        altman_z_score=altman_z
    )

@router.get("/", response_model=List[CompanyOut])
def get_companies(db: Session = Depends(get_db), current_user = Depends(require_analyst)):
    """
    Get all registered companies.
    """
    return db.query(Company).order_by(Company.name).all()

@router.get("/{company_id}", response_model=CompanyOut)
def get_company_by_id(company_id: int, db: Session = Depends(get_db), current_user = Depends(require_analyst)):
    """
    Retrieve details of a single company profile.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@router.get("/{company_id}/risk-profile", response_model=RiskProfileOut)
def get_company_risk_profile(company_id: int, db: Session = Depends(get_db), current_user = Depends(require_analyst)):
    """
    Retrieve risk metrics (Altman, Debt/Equity, current ratio) for a company.
    """
    profile = db.query(RiskProfile).filter(RiskProfile.company_id == company_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Risk profile not found for this company")
    return profile

@router.post("/", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
def create_company(
    company_in: CompanyCreate, 
    db: Session = Depends(get_db), 
    current_user = Depends(require_analyst)
):
    """
    Create a new company. If financial statements metrics are provided, 
    automatically computes and generates its corresponding RiskProfile.
    """
    db_company = db.query(Company).filter(Company.name == company_in.name).first()
    if db_company:
        raise HTTPException(status_code=400, detail="Company with this name already exists")

    company = Company(
        name=company_in.name,
        ticker=company_in.ticker.upper(),
        industry=company_in.industry,
        financial_summary=company_in.financial_summary
    )
    db.add(company)
    db.commit()
    db.refresh(company)

    # Compute risk profile if financial parameters were passed
    if company_in.financial_summary:
        try:
            profile = calculate_financial_ratios(company.id, company_in.financial_summary)
            db.add(profile)
            db.commit()
        except Exception as e:
            # Clean up created company if ratio calculation crashed
            db.delete(company)
            db.commit()
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid financial summary parameters. Ratio calculation failed: {e}"
            )
            
    return company
