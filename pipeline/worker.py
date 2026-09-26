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
import time

from rq import Worker
from rq.registry import ScheduledJobRegistry

from pipeline.queue import QUEUE_AGGREGATE, QUEUE_CLASSIFY, QUEUE_EXTRACT, get_redis

# force=True: pipeline.config sets an INFO default on import, and basicConfig
# is first-call-wins. Without this the format here depends on import order.
logging.basicConfig(
    force=True, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def run_worker(queues: list[str] = None, burst: bool = False):
    if queues is None:
        queues = [QUEUE_AGGREGATE, QUEUE_EXTRACT, QUEUE_CLASSIFY]

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
    burst = "--burst" in args
    run_worker([a for a in args if a != "--burst"] or None, burst=burst)
