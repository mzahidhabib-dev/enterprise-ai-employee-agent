# src/db/database.py
"""
Database connection setup for the AI Employee Agent.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Expects a standard PostgreSQL connection string
# e.g., postgresql://postgres:password@localhost:5432/ai_agent
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agent.db")

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Generator to provide a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
