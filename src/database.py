from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.orm import declarative_base



BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "transactions.db"

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ✅ THIS FUNCTION IS REQUIRED
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
