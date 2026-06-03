from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from backend.app.database import get_db
from backend.app.models import RegulatoryReference
from backend.app.schemas import RegulatoryReferenceCreate, RegulatoryReferenceOut
from backend.app.auth import require_admin, require_analyst
from backend.app.rag import reindex_references, search_regulatory_references

router = APIRouter(prefix="/regulatory", tags=["Regulatory References"])

@router.get("/search", response_model=List[Dict[str, Any]])
def search_references(
    q: str, 
    k: int = 3, 
    db: Session = Depends(get_db),
    current_user = Depends(require_analyst)
):
    """
    Search regulatory guidelines using FAISS/RAG matching.
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty")
    return search_regulatory_references(q, db, k)

@router.get("/", response_model=List[RegulatoryReferenceOut])
def list_references(db: Session = Depends(get_db), current_user = Depends(require_analyst)):
    """
    Retrieve list of all registered regulatory references.
    """
    return db.query(RegulatoryReference).order_by(RegulatoryReference.source).all()

@router.post("/", response_model=RegulatoryReferenceOut, status_code=status.HTTP_201_CREATED)
def create_reference(
    ref_in: RegulatoryReferenceCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Insert a new regulatory reference and index it (Admin only).
    """
    new_ref = RegulatoryReference(
        source=ref_in.source.upper(),
        section=ref_in.section,
        content=ref_in.content
    )
    db.add(new_ref)
    db.commit()
    db.refresh(new_ref)
    
    # Automatically reindex vectors
    reindex_references(db)
    
    return new_ref

@router.post("/reindex", status_code=status.HTTP_200_OK)
def trigger_reindex(db: Session = Depends(get_db), current_user = Depends(require_admin)):
    """
    Manually rebuild FAISS vector index (Admin only).
    """
    success = reindex_references(db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to build FAISS vector index. Check backend logs."
        )
    return {"message": "FAISS vector index rebuilt successfully"}
