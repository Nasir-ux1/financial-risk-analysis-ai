import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from backend.app.database import engine, Base, SessionLocal
from backend.app.models import User, Company, RegulatoryReference
from backend.app.auth import get_password_hash
from backend.app.routes.companies import calculate_financial_ratios
from backend.app.rag import reindex_references

def seed_db():
    print("Initializing database tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    try:
        # 1. Seed Users
        print("Seeding users (credentials hashed with bcrypt)...")
        users = [
            User(
                email="admin@riskai.com",
                hashed_password=get_password_hash("adminpassword"),
                role="ADMIN"
            ),
            User(
                email="analyst@riskai.com",
                hashed_password=get_password_hash("analystpassword"),
                role="ANALYST"
            )
        ]
        db.add_all(users)
        db.commit()
        print("  -> Seeding complete. Credentials:")
        print("     * Analyst: analyst@riskai.com / analystpassword")
        print("     * Admin: admin@riskai.com / adminpassword")

        # 2. Seed Companies
        print("Seeding companies & computing financial risk profiles...")
        companies_data = [
            {
                "name": "Global Energy Corp",
                "ticker": "GEC",
                "industry": "Energy",
                "financial_summary": {
                    "total_assets": 12000000.0,
                    "total_liabilities": 9000000.0,
                    "current_assets": 4500000.0,
                    "current_liabilities": 5000000.0,
                    "retained_earnings": 1500000.0,
                    "ebit": 400000.0,
                    "revenue": 14000000.0,
                    "market_equity": 3000000.0,
                    "interest_expense": 350000.0
                }
            },
            {
                "name": "Nova Tech Ltd",
                "ticker": "NVT",
                "industry": "Technology",
                "financial_summary": {
                    "total_assets": 8500000.0,
                    "total_liabilities": 2500000.0,
                    "current_assets": 5000000.0,
                    "current_liabilities": 2000000.0,
                    "retained_earnings": 4000000.0,
                    "ebit": 1800000.0,
                    "revenue": 9500000.0,
                    "market_equity": 6000000.0,
                    "interest_expense": 80000.0
                }
            },
            {
                "name": "Apex Builders S.A.",
                "ticker": "ABS",
                "industry": "Real Estate",
                "financial_summary": {
                    "total_assets": 22000000.0,
                    "total_liabilities": 18500000.0,
                    "current_assets": 7000000.0,
                    "current_liabilities": 9500000.0,
                    "retained_earnings": -800000.0,
                    "ebit": -200000.0,
                    "revenue": 8000000.0,
                    "market_equity": 3500000.0,
                    "interest_expense": 900000.0
                }
            }
        ]
        
        for c_data in companies_data:
            company = Company(
                name=c_data["name"],
                ticker=c_data["ticker"],
                industry=c_data["industry"],
                financial_summary=c_data["financial_summary"]
            )
            db.add(company)
            db.commit()
            db.refresh(company)
            
            # Compute ratios
            profile = calculate_financial_ratios(company.id, c_data["financial_summary"])
            db.add(profile)
            db.commit()
            print(f"  -> Profile generated for {company.name}: Rating={profile.risk_rating}, Score={profile.overall_score}, Altman={profile.altman_z_score}")

        # 3. Seed Regulatory References
        print("Seeding regulatory guidelines framework...")
        references_data = [
            # Basel III
            {
                "source": "BASEL_III",
                "section": "Section 14: Leverage Ratio Framework",
                "content": "The Basel III framework introduces a leverage ratio metric as a non-risk-based backstop. The minimum leverage ratio is set at 3%. A leverage ratio (measured as Tier 1 Capital / Total Exposure) below 3.0% indicates capital inadequacy and increases system risk. Financial entities must verify that debt-to-equity ratios remain aligned with risk margins, where ratios above 2.0 warrant secondary monitoring."
            },
            {
                "source": "BASEL_III",
                "section": "Section 28: Liquidity Coverage Ratio (LCR)",
                "content": "The LCR requires institutions to maintain a stock of high-quality liquid assets (HQLA) that is sufficient to meet total net cash outflows over a 30-day stress scenario. The target current ratio is expected to stay above 1.15 in stress environments. Ratios under 1.0 indicate critical short-term insolvency hazards."
            },
            # IFRS 9
            {
                "source": "IFRS_9",
                "section": "Standard 5.5: Impairment & Expected Credit Losses (ECL)",
                "content": "IFRS 9 introduces a three-stage model for impairment. Stage 1 covers assets with no significant increase in credit risk since initial recognition (12-month ECL). Stage 2 applies when a Significant Increase in Credit Risk (SICR) is detected (Lifetime ECL). An Altman Z-score dropping below 2.9 (Grey Zone) or an interest coverage ratio below 1.5 triggers Stage 2 classification."
            },
            {
                "source": "IFRS_9",
                "section": "Standard 5.5.15: Default Identification",
                "content": "Financial instruments are classified as Stage 3 (Default/Impaired) when objective evidence of default exists. Key defaults indicators include: a debt-to-equity ratio exceeding 4.0, negative Altman Z-score (distress zone < 1.8), interest coverage ratio below 1.0, or past due obligations exceeding 90 days."
            },
            # SEC Rules
            {
                "source": "SEC_10K",
                "section": "Item 7A: Quantitative Disclosures of Market Risk",
                "content": "Public companies must disclose market risk sensitivity, debt covenants, and credit arrangements. If interest coverage ratios slide below covenants thresholds (frequently 2.0x), entities must state liquidity relief terms. Failure to comply with covenants leads to Technical Default."
            }
        ]
        
        for r_data in references_data:
            ref = RegulatoryReference(
                source=r_data["source"],
                section=r_data["section"],
                content=r_data["content"]
            )
            db.add(ref)
        db.commit()
        print(f"  -> Seeded {len(references_data)} regulatory reference guidelines.")

        # 4. Compile vector store
        print("Compiling FAISS vector database from seed data...")
        reindex_references(db)
        print("Database seeding completed successfully.")

    except Exception as e:
        db.rollback()
        print(f"Seeding failed with error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
