"""The FastAPI app: middleware, mounts, and the routers that do the work.

api/models.py    every shape the API accepts or returns
api/queries.py   every SQL string
api/gate.py      row -> Memory, redacted unless you are standing there
api/read.py      the read endpoints
api/write.py     unlock, media, submissions, reports
api/accounts.py  /v1/me and /v1/auth/*
api/privacy.py   the policy both app stores require
api/card.py      the server-rendered card
api/embed.py     the embeddable map
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.accounts import router as accounts_router
from api.card import router as card_router
from api.embed import router as embed_router
from api.media import MEDIA_DIR, MEDIA_URL_PREFIX, NoSniff
from api.privacy import router as privacy_router
from api.read import router as read_router
from api.write import router as write_router

app = FastAPI(
    title="Memory Lane API",
    description="Query location-based memories from video content",
    version="1.0.0",
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
app.include_router(card_router)

# api/embed.py ships OpenStreetMap's public tiles, whose usage policy this would
# violate on a real host - its own comment says "DO NOT put this embed on a
# public host until this line changes". That guard was a comment while
# railway.json deploys this app unconditionally, so it is a switch now.
if os.getenv("ENABLE_EMBED", "1") != "0":
    app.include_router(embed_router)


@app.get("/")
def root():
    """API root - health check. railway.json points at this."""
    return {"status": "ok", "service": "memory-lane"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
