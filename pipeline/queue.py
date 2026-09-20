"""Redis queue setup and utilities."""

import os
from redis import Redis
from rq import Queue
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_redis_conn = None


def get_redis() -> Redis:
    """Get Redis connection (singleton)."""
    global _redis_conn
    if _redis_conn is None:
        _redis_conn = Redis.from_url(REDIS_URL)
    return _redis_conn


def get_queue(name: str = "default") -> Queue:
    """Get RQ queue by name."""
    return Queue(name, connection=get_redis())


# Queue names
QUEUE_CLASSIFY = "classify"  # Haiku pre-filter
QUEUE_EXTRACT = "extract"  # Sonnet extraction
QUEUE_AGGREGATE = "aggregate"  # Merge results
