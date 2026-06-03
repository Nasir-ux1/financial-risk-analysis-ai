import os
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RAG")

# Attempt imports for LangChain and FAISS
try:
    from langchain_core.embeddings import Embeddings
    from langchain_community.vectorstores import FAISS
    from langchain_core.documents import Document
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    FAISS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"LangChain or FAISS import error: {e}. Falling back to database keyword matcher.")
    FAISS_AVAILABLE = False

# We implement a lightweight, deterministic Embedding class for local dev/demo
# that doesn't require PyTorch, TensorFlow, or active network calls,
# but remains fully compatible with LangChain's Embeddings interface.
if FAISS_AVAILABLE:
    class SimpleHashEmbeddings(Embeddings):
        """
        Deterministic string-to-vector embedding using a word-hashing approach.
        Generates 128-dimensional vectors. Good for local testing and demo.
        If an Anthropic/OpenAI or HuggingFace model is desired in production,
        it can be drop-in replaced here.
        """
        def __init__(self):
            self.dim = 128

        def _embed(self, text: str) -> List[float]:
            # Convert text to lower case and tokenize simply
            words = text.lower().split()
            vector = [0.0] * self.dim
            if not words:
                return vector
                
            # Assign weights to dimensions based on character hash values
            for word in words:
                val = 0
                for char in word:
                    val = val * 31 + ord(char)
                idx = abs(val) % self.dim
                vector[idx] += 1.0
                
            # Normalize vector (L2 norm)
            norm = sum(x * x for x in vector) ** 0.5
            if norm > 0:
                vector = [x / norm for x in vector]
            return vector

        def embed_documents(self, texts: List[str]) -> List[List[float]]:
            return [self._embed(text) for text in texts]

        def embed_query(self, text: str) -> List[float]:
            return self._embed(text)

# Local cache folder for FAISS index
VECTOR_STORE_DIR = "vector_store"

def reindex_references(db: Session) -> bool:
    """
    Reads regulatory references from SQL database, chunks them,
    indexes them into FAISS, and saves the vector store locally.
    """
    from backend.app.models import RegulatoryReference
    
    references = db.query(RegulatoryReference).all()
    if not references:
        logger.info("No regulatory references found in database to index.")
        return False

    if not FAISS_AVAILABLE:
        logger.warning("FAISS or LangChain not available. Skipping indexing (will use DB query search).")
        return False

    try:
        documents = []
        for ref in references:
            metadata = {
                "id": ref.id,
                "source": ref.source,
                "section": ref.section
            }
            # Create a langchain Document
            doc = Document(
                page_content=f"[{ref.source} - {ref.section}] {ref.content}",
                metadata=metadata
            )
            documents.append(doc)
            
        # Split documents into smaller chunks
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = text_splitter.split_documents(documents)
        
        # Build FAISS index
        embeddings = SimpleHashEmbeddings()
        db_vector = FAISS.from_documents(chunks, embeddings)
        
        # Save index locally
        os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
        db_vector.save_local(VECTOR_STORE_DIR)
        logger.info(f"Successfully indexed {len(chunks)} regulatory chunks into FAISS.")
        return True
    except Exception as e:
        logger.error(f"Error indexing FAISS vector store: {e}")
        return False

def search_regulatory_references(query: str, db: Session, k: int = 3) -> List[Dict[str, Any]]:
    """
    Searches the FAISS vector store.
    Falls back to a keyword-like query on SQL DB if FAISS is not loaded or missing.
    """
    results = []
    
    # Try FAISS search if available
    if FAISS_AVAILABLE and os.path.exists(VECTOR_STORE_DIR):
        try:
            embeddings = SimpleHashEmbeddings()
            db_vector = FAISS.load_local(VECTOR_STORE_DIR, embeddings, allow_dangerous_deserialization=True)
            search_results = db_vector.similarity_search_with_score(query, k=k)
            
            for doc, score in search_results:
                results.append({
                    "id": doc.metadata.get("id"),
                    "source": doc.metadata.get("source"),
                    "section": doc.metadata.get("section"),
                    "content": doc.page_content.split("] ", 1)[-1] if "] " in doc.page_content else doc.page_content,
                    "score": float(score)  # Lower is more similar in FAISS L2 distance
                })
            return results
        except Exception as e:
            logger.error(f"FAISS search failed, falling back to SQL search: {e}")
            
    # Fallback SQL search (keyword query on references table)
    from backend.app.models import RegulatoryReference
    
    logger.info("Executing database keyword-based search fallback.")
    # Simple keyword split and like query
    words = query.lower().split()
    if not words:
        return []
        
    # Find records containing any of the query words, order by matching count
    matches = db.query(RegulatoryReference).all()
    scored_matches = []
    for match in matches:
        score = 0
        content_lower = match.content.lower()
        source_lower = match.source.lower()
        section_lower = match.section.lower()
        
        for word in words:
            if word in content_lower:
                score += 3
            if word in section_lower:
                score += 2
            if word in source_lower:
                score += 1
                
        if score > 0:
            scored_matches.append((match, score))
            
    # Sort matches by score descending
    scored_matches.sort(key=lambda x: x[1], reverse=True)
    
    for match, score in scored_matches[:k]:
        results.append({
            "id": match.id,
            "source": match.source,
            "section": match.section,
            "content": match.content,
            "score": float(10.0 - score)  # Align score meaning (lower is better distance)
        })
        
    return results
