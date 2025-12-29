"""CLI to enqueue videos for extraction."""

import argparse
import logging

from pipeline.tasks import enqueue_all_pending, task_enqueue_chunks, get_extraction_status
from pipeline.queue import get_queue, QUEUE_CLASSIFY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Enqueue videos for memory extraction")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Enqueue all pending videos"
    )
    parser.add_argument(
        "--video",
        type=int,
        metavar="ID",
        help="Enqueue a specific video by content ID"
    )
    parser.add_argument(
        "--status",
        type=int,
        metavar="ID",
        help="Check extraction status for a video"
    )

    args = parser.parse_args()

    if args.status:
        status = get_extraction_status(args.status)
        print(f"Extraction status for content_id={args.status}:")
        for key, value in status.items():
            print(f"  {key}: {value}")
        return

    if args.video:
        logger.info(f"Enqueueing video {args.video}")
        queue = get_queue(QUEUE_CLASSIFY)
        job = queue.enqueue(task_enqueue_chunks, content_id=args.video, job_timeout="10m")
        print(f"Enqueued job: {job.id}")
        return

    if args.all:
        result = enqueue_all_pending()
        print(f"Enqueued {result['enqueued']} videos")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
