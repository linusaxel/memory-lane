"""The FastAPI app: middleware, mounts, and the routers that do the work.

api/models.py    every shape the API accepts or returns
api/queries.py   every SQL string
api/gate.py      row -> Memory, redacted unless you are standing there
api/read.py      the read endpoints
api/route_solver.py  which stops today's walk visits, and in what order
api/write.py     unlock, media, submissions, reports
api/accounts.py  /v1/me and /v1/auth/*
api/privacy.py   the policy both app stores require
api/card.py      the server-rendered card
api/embed.py     the embeddable map
"""

import logging
import os
from contextlib import asynccontextmanager

import anyio.to_thread
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from api.accounts import router as accounts_router
from api.billing import router as billing_router
from api.card import router as card_router
from api.embed import router as embed_router
from api.media import MEDIA_DIR, MEDIA_URL_PREFIX, NoSniff
from api.privacy import router as privacy_router
from api.read import router as read_router
from api.write import router as write_router
from pipeline.config import ENABLE_EMBED, MAX_CONCURRENCY, PUBLIC_HOST
from pipeline.db import get_session

# Uvicorn configures its own loggers only; without this, the API's own
# warnings reach stderr with no time on them and its info lines not at all.
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Run no more requests at once than the database can serve.

    Every endpoint here but one is a `def`, which FastAPI hands to anyio's
    thread pool - forty threads by default - and each one holds a session for
    the length of its body. The pool tops out at MAX_CONCURRENCY connections,
    so the ten threads past that would each occupy a thread *and* block on a
    connection, which is the same queue as before with a thread stapled to it.

    Capping the thread pool moves the waiting one step earlier, where it costs
    a slot in an event loop rather than a whole OS thread, and it means the two
    numbers cannot drift apart the next time somebody tunes one of them.
    """
    anyio.to_thread.current_default_thread_limiter().total_tokens = MAX_CONCURRENCY
    yield


app = FastAPI(
    title="Memory Lane API",
    description="Query location-based memories from video content",
    version="1.0.0",
    lifespan=lifespan,
    # A map of every endpoint is for us, not for whoever finds the host.
    docs_url=None if PUBLIC_HOST else "/docs",
    redoc_url=None if PUBLIC_HOST else "/redoc",
    openapi_url=None if PUBLIC_HOST else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    # A wildcard origin with credentials is rejected by browsers anyway, and the
    # mobile app sends no cookies. Set CORS_ORIGINS to lock this down for a web client.
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount(MEDIA_URL_PREFIX, NoSniff(directory=MEDIA_DIR), name="media")

app.include_router(privacy_router)
app.include_router(read_router)
app.include_router(write_router)
app.include_router(accounts_router)
app.include_router(billing_router)
app.include_router(card_router)

# Off on the public host unless asked for: pipeline/config.py.
if ENABLE_EMBED:
    app.include_router(embed_router)


@app.get("/")
def root(response: Response):
    """API root - health check. railway.json points at this, so a deploy that
    cannot reach its database fails there instead of going live."""
    try:
        with get_session() as session:
            session.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Health check: the database did not answer")
        response.status_code = 503
        return {"status": "no database", "service": "memory-lane"}
    return {"status": "ok", "service": "memory-lane"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
