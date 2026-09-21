"""Database connection and session management."""

import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from pipeline import config

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://memorylane:memorylane@localhost:5432/memorylane"
)

# Railway hands out postgresql:// URLs and SQLAlchemy would pick psycopg2.
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# Sized rather than defaulted: see DB_POOL_SIZE in pipeline/config.py for why
# five-plus-ten under a forty-thread server is a queue in the wrong place.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=config.DB_POOL_SIZE,
    max_overflow=config.DB_MAX_OVERFLOW,
    pool_timeout=config.DB_POOL_TIMEOUT,
)
SessionLocal = sessionmaker(bind=engine)


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_connection():
    with get_session() as session:
        result = session.execute(text("SELECT 1"))
        return result.scalar() == 1


if __name__ == "__main__":
    if check_connection():
        print("Database connection successful")
    else:
        print("Database connection failed")
