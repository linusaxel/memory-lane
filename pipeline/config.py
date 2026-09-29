"""Every environment knob the pipeline reads, in one place.

extract.py and tasks.py each used to read the same five variables, and the chunk
defaults were hardcoded a third time in chunk_transcript's signature. Three
sources of truth for one value is how CLASSIFIER_MODEL drifted to an ID that
does not exist.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# Set by Railway on every deploy, so the public host cannot forget to say it is
# one. There, nothing falls back to a dev value: no default DATABASE_URL, no
# /docs, and the embed is off unless ENABLE_EMBED=1.
PUBLIC_HOST = bool(os.getenv("RAILWAY_ENVIRONMENT_NAME"))
# api/embed.py ships OpenStreetMap's public tiles, whose usage policy a real
# host would violate.
ENABLE_EMBED = os.getenv("ENABLE_EMBED", "0" if PUBLIC_HOST else "1") != "0"

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
# blocked outright. A proxy URL (http://user:pass@host:port) spreads the load,
# and Webshare's rotating residential pool (it wins when set) gets past it;
# the delay is the mean pause between fetches, jittered so they do not tick.
TRANSCRIPT_PROXY = os.getenv("TRANSCRIPT_PROXY") or None
WEBSHARE_PROXY_USERNAME = os.getenv("WEBSHARE_PROXY_USERNAME") or None
WEBSHARE_PROXY_PASSWORD = os.getenv("WEBSHARE_PROXY_PASSWORD") or None
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

# An OSRM `foot` server (osrm/build.sh) for today's route. Empty means
# crow-flies - api/streets.py.
ROUTING_URL = (os.getenv("ROUTING_URL") or "").rstrip("/") or None

# Photon, the OpenStreetMap geocoder (pipeline/geocode.py). The public server
# asks for about one request a second; a self-hosted country extract is the
# same API at another URL.
PHOTON_URL = (os.getenv("PHOTON_URL") or "https://photon.komoot.io").rstrip("/")

# What people post is screened by CLASSIFIER_MODEL before it is public
# (api/moderation.py). Off for tests and e2e, which must not call out.
SCREEN_POSTS = os.getenv("SCREEN_POSTS", "1") == "1"

# The address the privacy policy gives for questions and data requests. Unset,
# the policy says one is coming rather than inventing one.
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL") or None

# RevenueCat sells the subscription; api/billing.py records it
# (docs/10-decisions.md#revenuecat-sells-it-our-table-decides). The webhook
# secret is what RevenueCat sends as its Authorization header; the API key is
# the server-side secret key, never the app's public one. Either empty and
# /v1/billing/* answers 503.
REVENUECAT_WEBHOOK_SECRET = os.getenv("REVENUECAT_WEBHOOK_SECRET") or None
REVENUECAT_API_KEY = os.getenv("REVENUECAT_API_KEY") or None
