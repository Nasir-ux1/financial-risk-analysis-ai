import json
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.database import get_db
from backend.app.models import AssessmentHistory, Company, RiskProfile, User
from backend.app.schemas import AssessmentRequest, AssessmentOut, PromptCompareRequest, PromptCompareResponse, PromptCompareResult
from backend.app.auth import require_analyst, get_current_user
from backend.app.rag import search_regulatory_references
from backend.app.risk_analyst import analyze_risk_with_llm, evaluate_assessment_as_judge
from backend.app.routes.companies import calculate_financial_ratios

router = APIRouter(prefix="/assessments", tags=["Assessments"])

@router.get("/history", response_model=List[AssessmentOut])
def get_assessment_history(db: Session = Depends(get_db), current_user: User = Depends(require_analyst)):
    """
    Retrieve logs of all past credit risk assessments.
    """
    return db.query(AssessmentHistory).order_by(AssessmentHistory.created_at.desc()).all()

@router.get("/{assessment_id}", response_model=AssessmentOut)
def get_assessment_detail(
    assessment_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_analyst)
):
    """
    Retrieve logs of a single credit risk assessment.
    """
    assessment = db.query(AssessmentHistory).filter(AssessmentHistory.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment

@router.post("/", response_model=AssessmentOut, status_code=status.HTTP_201_CREATED)
def create_assessment(
    req: AssessmentRequest, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_analyst)
):
    """
    Performs a credit risk assessment query. 
    Retrieves regulatory rules from FAISS, queries Claude with selected prompt variant,
    grades results via LLM-as-a-Judge, and records it in history.
    """
    # 1. Fetch company financial ratios if company_id is provided
    company_metrics = {}
    company_name = "General Assessment"
    if req.company_id:
        company = db.query(Company).filter(Company.id == req.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        company_name = company.name
        
        # Fetch ratios
        profile = db.query(RiskProfile).filter(RiskProfile.company_id == req.company_id).first()
        if profile:
            company_metrics = {
                "name": company.name,
                "ticker": company.ticker,
                "debt_to_equity": profile.debt_to_equity,
                "current_ratio": profile.current_ratio,
                "interest_coverage": profile.interest_coverage,
                "altman_z_score": profile.altman_z_score,
                "overall_risk_score": profile.overall_score,
                "risk_rating": profile.risk_rating
            }
        else:
            company_metrics = {"name": company.name, "ticker": company.ticker}

    # 2. Query RAG vector store for relevant regulatory clauses
    search_query = f"{req.query} {company_name}"
    references = search_regulatory_references(search_query, db, k=3)
    
    # Format context string for Claude
    context_parts = []
    citations_data = []
    for ref in references:
        ref_str = f"[{ref['source']} - {ref['section']}] {ref['content']}"
        context_parts.append(ref_str)
        citations_data.append({
            "source": ref["source"],
            "section": ref["section"],
            "content": ref["content"]
        })
    context_str = "\n\n".join(context_parts) if context_parts else "No specific regulatory guidelines retrieved."

    # 3. Analyze credit risk using selected prompt engineering variant
    analysis_res = analyze_risk_with_llm(req.query, company_metrics, context_str, req.prompt_variant)
    
    # Normalize output from Claude formats
    assessment_text = analysis_res.get("assessment", "")
    if not assessment_text and "reasoning_chain" in analysis_res:
        # For CoT, include reasoning chain and structured assessment
        assessment_text = f"REASONING CHAIN:\n{analysis_res['reasoning_chain']}\n\nASSESSMENT:\n{analysis_res.get('assessment', '')}"
    elif not assessment_text:
        assessment_text = str(analysis_res)

    confidence = analysis_res.get("confidence_score", 0.5)

    # 4. Trigger LLM-as-a-Judge Quality Grading
    acc, comp, reg, feedback = evaluate_assessment_as_judge(
        req.query, company_metrics, context_str, assessment_text, req.prompt_variant
    )

    # 5. Save report to DB history
    history_item = AssessmentHistory(
        company_id=req.company_id,
        query=req.query,
        prompt_variant=req.prompt_variant,
        assessment_text=assessment_text,
        confidence_score=confidence,
        sources=citations_data,
        judge_accuracy=acc,
        judge_completeness=comp,
        judge_regulatory_alignment=reg,
        judge_feedback=feedback,
        created_by=current_user.id
    )
    db.add(history_item)
    db.commit()
    db.refresh(history_item)
    
    return history_item


@router.post("/compare", response_model=PromptCompareResponse)
def compare_prompt_variants(
    req: PromptCompareRequest, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_analyst)
):
    """
    Run the same credit risk assessment query across ALL THREE prompt variants.
    Grades all three using LLM-as-a-Judge and returns a comparative analysis.
    """
    # 1. Fetch company ratios
    company_metrics = {}
    company_name = "General Assessment"
    if req.company_id:
        company = db.query(Company).filter(Company.id == req.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        company_name = company.name
        profile = db.query(RiskProfile).filter(RiskProfile.company_id == req.company_id).first()
        if profile:
            company_metrics = {
                "name": company.name,
                "ticker": company.ticker,
                "debt_to_equity": profile.debt_to_equity,
                "current_ratio": profile.current_ratio,
                "interest_coverage": profile.interest_coverage,
                "altman_z_score": profile.altman_z_score,
                "overall_risk_score": profile.overall_score,
                "risk_rating": profile.risk_rating
            }

    # 2. Query FAISS corpus
    search_query = f"{req.query} {company_name}"
    references = search_regulatory_references(search_query, db, k=3)
    
    context_parts = []
    for ref in references:
        context_parts.append(f"[{ref['source']} - {ref['section']}] {ref['content']}")
    context_str = "\n\n".join(context_parts) if context_parts else "No specific regulatory guidelines retrieved."

    # 3. Iterate through Zero-shot, Few-shot, and Chain-of-thought variants
    variants = ["ZERO_SHOT", "FEW_SHOT", "COT"]
    results = []
    
    for var in variants:
        analysis_res = analyze_risk_with_llm(req.query, company_metrics, context_str, var)
        
        assessment_text = analysis_res.get("assessment", "")
        if not assessment_text and "reasoning_chain" in analysis_res:
            assessment_text = f"REASONING CHAIN:\n{analysis_res['reasoning_chain']}\n\nASSESSMENT:\n{analysis_res.get('assessment', '')}"
        elif not assessment_text:
            assessment_text = str(analysis_res)

        confidence = analysis_res.get("confidence_score", 0.5)

        # Grade using Judge
        acc, comp, reg, feedback = evaluate_assessment_as_judge(
            req.query, company_metrics, context_str, assessment_text, var
        )
        
        results.append(PromptCompareResult(
            prompt_variant=var,
            assessment_text=assessment_text,
            confidence_score=confidence,
            judge_accuracy=acc,
            judge_completeness=comp,
            judge_regulatory_alignment=reg,
            judge_feedback=feedback
        ))

    return PromptCompareResponse(
        query=req.query,
        results=results
    )


@router.post("/upload-statement")
async def upload_financial_statement(
    file: UploadFile = File(...),
    company_name: Optional[str] = None,
    ticker: Optional[str] = None,
    industry: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_analyst)
):
    """
    Parses an uploaded financial statement (JSON file format) containing balance sheet / income figures.
    Inserts/updates the company and returns the newly calculated financial ratios.
    """
    try:
        content = await file.read()
        financials = json.loads(content)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse statement. Please upload a valid JSON file. Details: {e}"
        )
        
    # Gather metadata with fallbacks
    c_name = company_name or financials.get("company_name", "Uploaded Corp")
    c_ticker = ticker or financials.get("ticker", "UPL").upper()
    c_industry = industry or financials.get("industry", "Technology")
    
    # Check if company already exists
    company = db.query(Company).filter(Company.name == c_name).first()
    if company:
        company.financial_summary = financials
        db.commit()
        db.refresh(company)
        
        # Recompute profile
        profile = db.query(RiskProfile).filter(RiskProfile.company_id == company.id).first()
        if profile:
            db.delete(profile)
            db.commit()
    else:
        company = Company(
            name=c_name,
            ticker=c_ticker,
            industry=c_industry,
            financial_summary=financials
        )
        db.add(company)
        db.commit()
        db.refresh(company)

    # Compute risk profile
    try:
        profile = calculate_financial_ratios(company.id, financials)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    except Exception as e:
        db.delete(company)
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"Financial parameters calculation failed: {e}"
        )

    return {
        "message": f"Successfully parsed and registered statement for {c_name}.",
        "company_id": company.id,
        "company_name": company.name,
        "ratios": {
            "overall_score": profile.overall_score,
            "risk_rating": profile.risk_rating,
            "debt_to_equity": profile.debt_to_equity,
            "current_ratio": profile.current_ratio,
            "interest_coverage": profile.interest_coverage,
            "altman_z_score": profile.altman_z_score
        }
    }
