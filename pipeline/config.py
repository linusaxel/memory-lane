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
# Shorter videos are never transcribed or extracted. On the channel this was
# set against, every clip is under 17 minutes and every episode over 60: a clip
# re-tells a story from its episode, so extracting it pays twice for a
# duplicate memory. Unknown durations (hand-listed videos) are never filtered.
MIN_VIDEO_MINUTES = int(os.getenv("MIN_VIDEO_MINUTES", "20"))
# YouTube blocks an IP that fetches too many transcripts, and cloud IPs are
# blocked outright. A proxy URL (http://user:pass@host:port) spreads the load;
# the delay is the mean pause between fetches, jittered so they do not tick.
TRANSCRIPT_PROXY = os.getenv("TRANSCRIPT_PROXY") or None
TRANSCRIPT_DELAY_SECONDS = float(os.getenv("TRANSCRIPT_DELAY_SECONDS", "1.5"))

# Sized so the connection pool and anyio's thread pool cannot drift apart -
# docs/10-decisions.md#the-pool-is-sized-to-the-server-and-the-server-to-the-pool.
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "5"))

#: Concurrent requests one process will run. Never more than the pool can serve.
MAX_CONCURRENCY = DB_POOL_SIZE + DB_MAX_OVERFLOW

# A ceiling on any single statement - docs/10-decisions.md#one-statement-cannot-run-for-ever.
DB_STATEMENT_TIMEOUT_MS = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "30000"))
