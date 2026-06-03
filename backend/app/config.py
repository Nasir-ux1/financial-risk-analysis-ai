import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    PROJECT_NAME: str = "Financial Risk Analysis AI Assistant"
    PROJECT_VERSION: str = "1.0.0"
    
    # Database configuration (PostgreSQL)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/financial_risk"
    )
    
    # Fallback to SQLite if PostgreSQL fails
    SQLITE_FALLBACK_URL: str = "sqlite:///./financial_risk.db"
    
    # JWT security settings
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", "9a15f01e7d23d8c1cfa2a8f8de80ab260a92004245c11bc0480b06b74e2d31a5"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    
    # Claude API configuration
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # App environment (development/production)
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

settings = Settings()
