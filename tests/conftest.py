# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.database import Base, get_db
from app import models

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

@pytest.fixture(autouse=True)
def clean_db():
    yield
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM transactions"))
        conn.execute(text("DELETE FROM users"))
        conn.commit()
        
# ✅ Create tables ONCE per test session
@pytest.fixture(scope="session", autouse=True)
def create_test_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Make sure you're dropping and recreating tables
@pytest.fixture
def client():
    # Clear ALL tables before each test
    from app.database import Base, engine
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    from app.main import app
    from fastapi.testclient import TestClient
    yield TestClient(app)
