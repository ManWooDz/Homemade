import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False) if engine else None


def get_db():
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL not set — check backend/.env")
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
