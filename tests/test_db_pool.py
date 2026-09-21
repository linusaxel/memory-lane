"""How many requests this API can be doing at once, and for how long it waits.

Three numbers have to stay in a particular order and live in three different
files, which is exactly the shape of thing that drifts:

  * SQLAlchemy's connection pool, in `pipeline/config.py`
  * anyio's thread pool, which FastAPI runs every `def` endpoint on
  * the app's own request timeout, in `mobile/src/api.ts`

Nothing fails loudly when they disagree. The API just gets slower under load
than it should, holding threads that are waiting for connections that are not
coming, and handing those connections to clients that gave up seconds ago.
"""

import pathlib
import re

import pytest

from pipeline.config import DB_MAX_OVERFLOW, DB_POOL_SIZE, DB_POOL_TIMEOUT, MAX_CONCURRENCY

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_the_pool_can_serve_every_request_the_server_will_run():
    """A thread that cannot get a connection is worse than a request that
    never got a thread: it costs an OS thread to do the same waiting."""
    assert MAX_CONCURRENCY == DB_POOL_SIZE + DB_MAX_OVERFLOW


def test_the_engine_is_built_to_that_size():
    """The defaults are 5 + 10, which is a quarter of the server's threads."""
    from pipeline.db import engine

    assert engine.pool.size() == DB_POOL_SIZE
    assert engine.pool._max_overflow == DB_MAX_OVERFLOW
    assert engine.pool._timeout == DB_POOL_TIMEOUT


def test_the_server_will_not_run_more_requests_than_the_pool_can_serve():
    """The cap is applied in a lifespan hook, and anyio's limiter is a RunVar -
    one per event loop - so it has to be read inside the same loop that set it.
    Reading it from anywhere else gets a fresh default and proves nothing."""
    import anyio
    import anyio.to_thread

    from api.main import app, lifespan

    seen = {}

    async def run():
        before = anyio.to_thread.current_default_thread_limiter().total_tokens
        async with lifespan(app):
            seen["before"] = before
            seen["after"] = anyio.to_thread.current_default_thread_limiter().total_tokens

    anyio.run(run)

    assert seen["after"] == MAX_CONCURRENCY
    assert seen["before"] > MAX_CONCURRENCY, (
        "anyio's default is no longer wider than the pool, so this cap may have "
        "stopped being the thing that keeps threads off an exhausted pool"
    )


def test_a_request_gives_up_on_the_pool_before_the_app_gives_up_on_it():
    """Waiting 30s for a connection serves a client that stopped listening at
    8s. The wait has to be the shorter of the two."""
    api_ts = (ROOT / "mobile" / "src" / "api.ts").read_text()
    match = re.search(r"REQUEST_TIMEOUT_MS\s*=\s*(\d+)", api_ts)
    assert match, "mobile/src/api.ts no longer declares REQUEST_TIMEOUT_MS"
    client_timeout_s = int(match.group(1)) / 1000

    assert DB_POOL_TIMEOUT < client_timeout_s, (
        f"the pool waits {DB_POOL_TIMEOUT}s for a connection but the app has "
        f"given up after {client_timeout_s}s"
    )


@pytest.mark.parametrize("knob", ["DB_POOL_SIZE", "DB_MAX_OVERFLOW", "DB_POOL_TIMEOUT"])
def test_every_knob_is_an_environment_variable(knob):
    """pipeline/config.py is where env knobs live; a hardcoded pool cannot be
    tuned on the host that actually has the load."""
    assert knob in (ROOT / "pipeline" / "config.py").read_text()
    assert f'os.getenv("{knob}"' in (ROOT / "pipeline" / "config.py").read_text()
