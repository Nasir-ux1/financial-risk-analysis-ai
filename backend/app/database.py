import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Database")

# Determine engine based on connection success
engine = None
db_url = settings.DATABASE_URL

# Check if SQLite url needs to be enforced (e.g. for simple tests)
if "sqlite" in db_url.lower():
    logger.info("Using SQLite database as configured.")
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
else:
    # Try connecting to PostgreSQL
    try:
        logger.info(f"Connecting to PostgreSQL at: {db_url.split('@')[-1] if '@' in db_url else db_url}")
        engine = create_engine(db_url, pool_pre_ping=True)
        # Force a quick connection check
        connection = engine.connect()
        connection.close()
        logger.info("Successfully connected to PostgreSQL database.")
    except Exception as e:
        logger.warning(
            f"Failed to connect to PostgreSQL: {e}. Falling back to local SQLite database: {settings.SQLITE_FALLBACK_URL}"
        )
        db_url = settings.SQLITE_FALLBACK_URL
        engine = create_engine(db_url, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
