"""Database connection and session management."""

import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://memorylane:memorylane@localhost:5432/memorylane"
)

# Convert to psycopg3 dialect if using default postgresql://
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


@contextmanager
def get_session():
    """Provide a transactional scope around a series of operations."""
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
    """Verify database connection is working."""
    with get_session() as session:
        result = session.execute(text("SELECT 1"))
        return result.scalar() == 1


if __name__ == "__main__":
    if check_connection():
        print("Database connection successful")
    else:
        print("Database connection failed")
