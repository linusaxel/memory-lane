"""RQ Worker entry point for memory extraction.

Re-execs itself on macOS before any other import -
docs/10-decisions.md#the-rq-worker-re-execs-itself-on-macos.
"""

import os
import sys

if sys.platform == "darwin" and os.environ.get("OBJC_DISABLE_INITIALIZE_FORK_SAFETY") != "YES":
    os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"
    # -m, not sys.argv[0]: running the file directly puts pipeline/ on sys.path
    # instead of the repo root, and every `from pipeline...` import then fails.
    os.execvp(sys.executable, [sys.executable, "-m", "pipeline.worker", *sys.argv[1:]])

import logging
import subprocess
import time
from collections import Counter

import anthropic
from rq import Queue, Worker
from rq.registry import ScheduledJobRegistry
from sqlalchemy import text

import pipeline.tasks  # noqa: F401  (loaded once, so a fork never imports a half-saved edit)
from pipeline.config import ANTHROPIC_API_KEY, CLASSIFIER_MODEL, EXTRACTION_MODEL
from pipeline.db import get_session
from pipeline.queue import QUEUE_AGGREGATE, QUEUE_CLASSIFY, QUEUE_EXTRACT, get_redis

# force=True: pipeline.config sets an INFO default on import, and basicConfig
# is first-call-wins. Without this the format here depends on import order.
logging.basicConfig(
    force=True, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def check_models():
    """Exit before the first job on a model ID the API refuses. A retired ID in
    .env otherwise fails every chunk, one at a time. Checked in a child: one
    HTTP call in this process and macOS segfaults every forked work-horse."""
    child = subprocess.run([sys.executable, "-c", "from pipeline.worker import _check; _check()"])
    if child.returncode:
        sys.exit(child.returncode)


def _check():
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    for name, model in (
        ("EXTRACTION_MODEL", EXTRACTION_MODEL),
        ("CLASSIFIER_MODEL", CLASSIFIER_MODEL),
    ):
        try:
            client.models.retrieve(model)
        except (
            anthropic.NotFoundError,
            anthropic.AuthenticationError,
            anthropic.PermissionDeniedError,
        ) as e:
            # Kept exploded with a trailing comma on purpose.
            # See docs/10-decisions.md#except-a-b-stays-exploded
            sys.exit(f"{name}={model!r} is not usable: {e}")
        except anthropic.APIError as e:
            logger.warning(f"Could not check {name}={model!r}, starting anyway: {e}")


QUEUES = [QUEUE_AGGREGATE, QUEUE_EXTRACT, QUEUE_CLASSIFY]


def _source_names(content_ids: set[int]) -> dict[int, str]:
    with get_session() as session:
        rows = session.execute(
            text("""
                SELECT c.id, COALESCE(s.name, 'no source') FROM content c
                LEFT JOIN sources s ON s.id = c.source_id
                WHERE c.id = ANY(:ids)
            """),
            {"ids": list(content_ids)},
        )
        return dict(rows.fetchall())


def confirm_queues(queues: list[str], yes: bool = False):
    """Say what the queues hold, by source, and ask before billing it. A queue
    left from an earlier day bills on the next run otherwise: 2026-09-30, 424
    forgotten jobs sat behind a one-book re-extraction."""
    conn = get_redis()
    jobs = {q: Queue(q, connection=conn).jobs for q in queues}
    if not any(jobs.values()):
        print("Nothing queued.")
        return
    names = _source_names({j.kwargs.get("content_id") for js in jobs.values() for j in js} - {None})
    for q, js in jobs.items():
        if js:
            by = Counter(names.get(j.kwargs.get("content_id"), "unknown") for j in js)
            print(f"{q}: {len(js)} jobs: " + ", ".join(f"{n} {c}" for n, c in by.most_common()))
    if yes:
        return
    if not sys.stdin.isatty():
        sys.exit("Not a terminal: pass --yes to run these.")
    if input("Run them? [y/N] ").strip().lower() != "y":
        sys.exit("Nothing run.")


def run_worker(queues: list[str] = None, burst: bool = False):
    if queues is None:
        queues = QUEUES

    check_models()

    logger.info(f"Starting worker for queues: {queues}")

    conn = get_redis()
    if not burst:
        Worker(queues, connection=conn).work(with_scheduler=True)
        return

    # rq's burst exits with retries still scheduled, which a later worker would
    # bill. Wait them out instead, so a burst leaves nothing behind.
    while True:
        Worker(queues, connection=conn).work(burst=True, with_scheduler=True)
        if not any(ScheduledJobRegistry(q, connection=conn).count for q in queues):
            return
        time.sleep(5)


if __name__ == "__main__":
    args = sys.argv[1:]
    queues = [a for a in args if a not in ("--burst", "--yes")] or QUEUES
    confirm_queues(queues, yes="--yes" in args)
    run_worker(queues, burst="--burst" in args)
