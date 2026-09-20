"""RQ Worker entry point for memory extraction."""

import logging
import sys

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
