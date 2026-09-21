"""Every environment knob the pipeline reads, in one place.

extract.py and tasks.py each used to read the same five variables, and the chunk
defaults were hardcoded a third time in chunk_transcript's signature. Three
sources of truth for one value is how CLASSIFIER_MODEL drifted to an ID that
does not exist.
"""

import os

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
EXTRACTION_MODEL = os.getenv("EXTRACTION_MODEL", "claude-sonnet-5")
CLASSIFIER_MODEL = os.getenv("CLASSIFIER_MODEL", "claude-haiku-4-5")
CHUNK_MINUTES = int(os.getenv("CHUNK_MINUTES", "4"))
CHUNK_OVERLAP_SECONDS = int(os.getenv("CHUNK_OVERLAP_SECONDS", "30"))

# How many database connections one API process may hold, and how long a
# request may wait for one.
#
# The defaults are not arbitrary. FastAPI runs a `def` handler - which is all
# but one of ours - on anyio's thread pool, forty threads wide by default, and
# every handler opens a session for its whole body. SQLAlchemy's own default
# pool is five connections plus ten overflow, so twenty-five of those forty
# threads could be parked on a pool that cannot grow, each holding a thread it
# cannot use. api/main.py narrows the thread pool to this ceiling for exactly
# that reason: queueing before a thread is taken is cheaper than queueing
# after, and it keeps the two numbers from drifting apart.
#
# The wait is short on purpose. The app gives up on any request after 8s
# (REQUEST_TIMEOUT_MS in mobile/src/api.ts), so a connection handed over at
# 30s is handed to nobody - it just holds the slot open for a client that has
# already gone. tests/test_db_pool.py keeps the two in that order.
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "5"))

#: Concurrent requests one process will run. Never more than the pool can serve.
MAX_CONCURRENCY = DB_POOL_SIZE + DB_MAX_OVERFLOW
