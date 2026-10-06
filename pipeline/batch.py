"""Extract chosen contents at half price, through the Message Batches API.

    python -m pipeline.batch --source "OpenStreetMap plaques"   # how many, nothing else
    python -m pipeline.batch --content 1036 1008 --run          # bills, at half price

It runs extract_all_pending over the chosen contents again and again. In a
pass, a call with no stored reply is not sent but collected
(`extract.COLLECT`), and its content stops there, pending, with nothing saved.
The calls go out as one batch; their replies are stored under the keys the
pipeline looks them up by, so the next pass reads them back and gets one stage
further: brief, chunks, judge, check, trim, retellings. When a pass collects
nothing, everything chosen is saved, and each content then gets what
aggregation gives it (`tasks.after_save`, sent as it comes, at full price).

A batch usually ends within the hour, at most 24, so a run is a handful of
passes. There is no Haiku pre-filter: every chunk goes to the extractor, at
half price. docs/10, *Extraction is batched*.
"""

import argparse
import logging
import time

import anthropic
from sqlalchemy import text

from pipeline import extract
from pipeline.db import get_session
from pipeline.extract import PENDING_EXTRACTION, Collect, log_cache, reply_text, store

logger = logging.getLogger(__name__)

POLL_SECONDS = 30
# Brief, chunks, judge, check, trim and one per retelling in a row: a content
# that needs more is stuck, not slow.
MAX_PASSES = 12


def chosen(session, content_ids: list[int] | None, source: str | None) -> list[int]:
    return list(
        session.execute(
            text(
                f"SELECT c.id {PENDING_EXTRACTION}"
                " AND (CAST(:ids AS int[]) IS NULL OR c.id = ANY(:ids))"
                " AND (CAST(:source AS text) IS NULL OR c.source_name = :source)"
                " ORDER BY c.id"
            ),
            {"ids": content_ids, "source": source},
        ).scalars()
    )


def send(client, requests: dict[str, dict], session) -> int:
    """One batch of `requests`, waited on; how many replies were stored."""
    batch = client.messages.batches.create(
        requests=[{"custom_id": key, "params": r["params"]} for key, r in requests.items()]
    )
    logger.info(f"Batch {batch.id}: {len(requests)} calls")
    while batch.processing_status != "ended":
        time.sleep(POLL_SECONDS)
        try:
            batch = client.messages.batches.retrieve(batch.id)
        except anthropic.APIConnectionError as e:
            # A network blip must not drop a batch that is already paid for.
            logger.warning(f"Batch {batch.id}: {e}; polling again")
            continue
        logger.info(f"Batch {batch.id}: {batch.request_counts}")
    stored = 0
    for result in client.messages.batches.results(batch.id):
        r = requests[result.custom_id]
        if result.result.type != "succeeded":
            logger.warning(f"[content:{r['content_id']}] {result.result.type}: {result.result}")
            continue
        log_cache(result.result.message)
        if (raw := reply_text(result.result.message)) is not None:
            store(
                session, result.custom_id, r["content_id"], r["chunk_index"], r["prompt_hash"], raw
            )
            stored += 1
    return stored


def run(client, content_ids: list[int]) -> None:
    from pipeline.tasks import _thin, after_save, seeded

    with get_session() as session:
        for row in session.execute(
            text(
                "SELECT c.id, c.title, c.source_type, t.segments FROM content c"
                " JOIN transcripts t ON t.content_id = c.id WHERE c.id = ANY(:ids)"
            ),
            {"ids": content_ids},
        ):
            if row.segments and _thin(row.source_type, row.segments):
                seeded(session, client, row.id, row.title, row.segments)

    for n in range(1, MAX_PASSES + 1):
        extract.COLLECT = Collect()
        try:
            extract.extract_all_pending(content_ids)
            pending = extract.COLLECT.requests
        finally:
            extract.COLLECT = None
        if not pending:
            break
        logger.info(f"Pass {n}: {len(pending)} calls wait on a batch")
        with get_session() as session:
            if not send(client, pending, session):
                raise SystemExit("A batch stored no reply; stopping rather than resending it")
    else:
        raise SystemExit(f"Still waiting after {MAX_PASSES} passes")

    with get_session() as session:
        done = list(
            session.execute(
                text("SELECT id FROM content WHERE id = ANY(:ids) AND memories_extracted"),
                {"ids": content_ids},
            ).scalars()
        )
    for content_id in done:
        after_save(client, content_id)
    logger.info(f"{len(done)} of {len(content_ids)} extracted")


def main():
    from pipeline.config import ANTHROPIC_API_KEY

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--content", type=int, nargs="+", help="content ids")
    parser.add_argument("--source", help="every pending content of one source, by name")
    parser.add_argument("--run", action="store_true", help="send the batches; bills")
    args = parser.parse_args()
    if not (args.content or args.source):
        parser.error("choose --content or --source: a batch never takes everything pending")
    with get_session() as session:
        ids = chosen(session, args.content, args.source)
    print(f"{len(ids)} pending: {ids[:20]}{' ...' if len(ids) > 20 else ''}")
    if args.run and ids:
        run(anthropic.Anthropic(api_key=ANTHROPIC_API_KEY), ids)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
