import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.database import Base, get_db
from backend.app.models import User
from backend.app.auth import get_password_hash, create_access_token

# Setup in-memory SQLite database engine for unit tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(name="db_session", scope="function")
def fixture_db_session():
    # Setup: Create tables
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    try:
        # Create default mock accounts
        analyst = User(
            email="test_analyst@riskai.com",
            hashed_password=get_password_hash("password123"),
            role="ANALYST"
        )
        admin = User(
            email="test_admin@riskai.com",
            hashed_password=get_password_hash("password123"),
            role="ADMIN"
        )
        db.add_all([analyst, admin])
        db.commit()
        
        yield db
    finally:
        db.close()
        # Teardown: Clean database
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(name="client")
def fixture_client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(name="analyst_headers")
def fixture_analyst_headers():
    token = create_access_token(data={"sub": "test_analyst@riskai.com", "role": "ANALYST"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="admin_headers")
def fixture_admin_headers():
    token = create_access_token(data={"sub": "test_admin@riskai.com", "role": "ADMIN"})
    return {"Authorization": f"Bearer {token}"}
