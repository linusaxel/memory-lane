"""RQ Worker entry point for memory extraction.

**On macOS this needs OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES in the
environment**, which the re-exec below arranges rather than leaving to whoever
runs it.

RQ forks a work horse per job, and a forked child that touches the Objective-C
runtime aborts: "may have been in progress in another thread when fork() was
called ... Crashing instead." Every job dies on signal 6, the queues drain into
nothing, and the worker log looks busy while achieving zero - which is a good
part of why the parallel path sat recorded as "untested locally".

Setting the variable from Python is too late: the runtime reads it before any
of this module runs. Measured - os.environ.setdefault here still produced 22
crashes out of 22 jobs. So the process replaces itself with one that has it.
"""

import os
import sys

# Before every other import, because the point is to get out of this process
# before anything initializes the runtime we are trying to appease.
# Must be set before any ObjC-linked import, and RQ's work horse forks:
# docs/10-decisions.md#the-rq-worker-re-execs-itself-on-macos
if sys.platform == "darwin" and os.environ.get("OBJC_DISABLE_INITIALIZE_FORK_SAFETY") != "YES":
    os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"
    # -m, not sys.argv[0]: running the file directly puts pipeline/ on sys.path
    # instead of the repo root, and every `from pipeline...` import then fails.
    os.execvp(sys.executable, [sys.executable, "-m", "pipeline.worker", *sys.argv[1:]])

import logging

from rq import Worker

from pipeline.queue import QUEUE_AGGREGATE, QUEUE_CLASSIFY, QUEUE_EXTRACT, get_redis

# force=True: pipeline.config sets an INFO default on import, and basicConfig
# is first-call-wins. Without this the format here depends on import order.
logging.basicConfig(
    force=True, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def run_worker(queues: list[str] = None):
    if queues is None:
        queues = [QUEUE_AGGREGATE, QUEUE_EXTRACT, QUEUE_CLASSIFY]

    logger.info(f"Starting worker for queues: {queues}")

    conn = get_redis()
    worker = Worker(queues, connection=conn)
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    queues = sys.argv[1:] if len(sys.argv) > 1 else None
    run_worker(queues)
