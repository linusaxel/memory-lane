"""Extract chosen contents at half price, through the Message Batches API.

    python -m pipeline.batch --source "OpenStreetMap plaques"   # how many, nothing else
    python -m pipeline.batch --content 1036 1008 --run          # bills, at half price

It runs extract_all_pending over the chosen contents again and again. In a
pass, a call with no stored reply is not sent but collected
(`extract.COLLECT`), and its content stops there, pending, with nothing saved.
The calls go out as one batch; their replies are stored under the keys the
pipeline looks them up by, so the next pass reads them back and gets one stage
further: a thin record's research, brief, chunks, judge, check, trim,
retellings. When a pass collects nothing, everything chosen is saved. Then
the same passes enrich the saved memories (`enrich.enrich_memories`:
research, structure, pick), and each content gets the rest of what
aggregation gives it (`tasks.after_save`, sent as it comes, at full price).

A batch usually ends within the hour, at most 24, so a run is a handful of
passes. There is no Haiku pre-filter: every chunk goes to the extractor, at
half price. docs/10, *Extraction is batched*.

A book goes scene-first (`scenes.extract_windows`), and so does any text with
`--scenes`: the same passes, so every card's fact sheet is made at half price.
`--render <source id>` writes a source's saved cards again from their sheets,
the writer and the check batched, then stored with `--apply`.
"""

import argparse
import logging
import time

import anthropic
from sqlalchemy import text

from pipeline import extract
from pipeline.db import get_session
from pipeline.extract import Collect, log_cache, pending_query, reply_text, store

logger = logging.getLogger(__name__)

POLL_SECONDS = 30
# Brief, chunks, judge, check, trim and one per retelling in a row; scene-first
# adds the book's index and note, the finder's second ask, the sheet and two
# rewrites, each one a check. A content that needs more is stuck, not slow.
MAX_PASSES = 20


def chosen(session, content_ids: list[int] | None, source: str | None) -> list[int]:
    return list(
        session.execute(
            text(
                f"SELECT c.id {pending_query(content_ids)}"
                " AND (CAST(:ids AS int[]) IS NULL OR c.id = ANY(:ids))"
                " AND (CAST(:source AS text) IS NULL OR c.source_name = :source)"
                " ORDER BY c.id"
            ),
            {"ids": content_ids, "source": source},
        ).scalars()
    )


def dropped(session, content_ids: list[int], ids: list[int]) -> list[str]:
    """Why each asked-for id is not pending, so a batch never runs nothing quietly."""
    missing = sorted(set(content_ids) - set(ids))
    rows = {
        r.id: r
        for r in session.execute(
            text(
                "SELECT c.id, s.status, c.memories_extracted, c.extraction_failed"
                " FROM content c LEFT JOIN sources s ON s.id = c.source_id"
                " WHERE c.id = ANY(:ids)"
            ),
            {"ids": missing},
        )
    }

    def why(r) -> str:
        if r is None:
            return "no such content"
        if r.status in ("candidate", "rejected"):
            return f"its source is {r.status}"
        if r.memories_extracted:
            return "already extracted"
        if r.extraction_failed:
            return "extraction failed"
        return "no transcript"

    return [f"{i}: {why(rows.get(i))}" for i in missing]


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
        if (raw := reply_text(result.result.message)) is None:
            logger.warning(f"[content:{r['content_id']}] {r['stage']} cut; raise its max_tokens")
            continue
        store(session, result.custom_id, r["content_id"], r["chunk_index"], r["prompt_hash"], raw)
        stored += 1
    return stored


def passes(client, step) -> str | None:
    """Run `step` pass after pass, each one's collected calls sent as one batch,
    until a pass collects nothing; why it stopped short, or None."""
    for n in range(1, MAX_PASSES + 1):
        extract.COLLECT = Collect()
        try:
            step(extract.COLLECT)
            pending = extract.COLLECT.requests
        finally:
            extract.COLLECT = None
        if not pending:
            return None
        logger.info(f"Pass {n}: {len(pending)} calls wait on a batch")
        with get_session() as session:
            if not send(client, pending, session):
                return "A batch stored no reply; stopping rather than resending it"
    return f"Still waiting after {MAX_PASSES} passes"


def run(client, content_ids: list[int], scene_first: bool = False) -> None:
    from pipeline import scenes
    from pipeline.enrich import enrich_memories
    from pipeline.tasks import _thin, after_save, seeded

    funnel = {}
    with get_session() as session:
        books = set(
            session.execute(
                text("SELECT id FROM content WHERE id = ANY(:ids) AND source_type = 'book'"),
                {"ids": content_ids},
            ).scalars()
        )
    by_scene = set(content_ids) if scene_first else books

    def extraction(collect: Collect) -> None:
        with get_session() as session:
            for row in session.execute(
                text(
                    "SELECT c.id, c.title, c.source_type, t.segments FROM content c"
                    " JOIN transcripts t ON t.content_id = c.id WHERE c.id = ANY(:ids)"
                    " AND NOT c.memories_extracted"
                ),
                {"ids": content_ids},
            ):
                if row.segments and _thin(row.source_type, row.segments):
                    seeded(session, client, row.id, row.title, row.segments)
        # A thin record still waiting on its research is not extracted without it.
        ready = [i for i in content_ids if i not in collect.stage]
        if old := [i for i in ready if i not in by_scene]:
            extract.extract_all_pending(old)
        if scene := [i for i in ready if i in by_scene]:
            scenes.extract_windows(client, scene)
        # Every pass replays every content; the last one it got through counts.
        funnel.update(collect.funnel)

    stopped = passes(client, extraction)

    with get_session() as session:
        done = list(
            session.execute(
                text("SELECT id FROM content WHERE id = ANY(:ids) AND memories_extracted"),
                {"ids": content_ids},
            ).scalars()
        )

    def enrichment(collect: Collect) -> None:
        with get_session() as session:
            for content_id in done:
                enrich_memories(session, client, content_id)

    # What enrichment still misses, after_save sends at full price.
    late = passes(client, enrichment)
    stopped = stopped or late
    for content_id in done:
        after_save(client, content_id)
    print_funnel(funnel)
    logger.info(f"{len(done)} of {len(content_ids)} extracted")
    # Stopping early still scores what was saved: a rerun never picks it up again.
    if stopped:
        raise SystemExit(stopped)


def render(client, source_id: int, apply: bool) -> None:
    """Every saved card of a source written again from its sheet: the passes
    batch the writer and the check, the last run reads them all back."""
    from pipeline import scenes

    def step(collect: Collect) -> None:
        with get_session() as session:
            scenes.rerender(session, client, source_id, False)

    if stopped := passes(client, step):
        raise SystemExit(stopped)
    with get_session() as session:
        scenes.rerender(session, client, source_id, apply)


def print_funnel(funnel: dict[int, dict]) -> None:
    """One line per content: how many each step kept. Placing drops the rest
    (the city as venue, outside the launch area, a retelling), each logged."""
    with get_session() as session:
        saved = dict(
            session.execute(
                text(
                    "SELECT content_id, count(*) FROM memories"
                    " WHERE content_id = ANY(:ids) GROUP BY content_id"
                ),
                {"ids": list(funnel)},
            ).all()
        )
    for content_id, steps in sorted(funnel.items()):
        counts = ", ".join(f"{n} {step}" for step, n in steps.items())
        print(f"content {content_id}: {counts}, {saved.get(content_id, 0)} saved")


def main():
    from pipeline.config import ANTHROPIC_API_KEY

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--content", type=int, nargs="+", help="content ids")
    parser.add_argument("--source", help="every pending content of one source, by name")
    parser.add_argument("--run", action="store_true", help="send the batches; bills")
    parser.add_argument("--scenes", action="store_true", help="scene-first with fact sheets")
    parser.add_argument("--render", type=int, metavar="SOURCE_ID", help="cards again from sheets")
    parser.add_argument("--apply", action="store_true", help="with --render, store the new cards")
    args = parser.parse_args()
    if args.render:
        if args.run:
            render(anthropic.Anthropic(api_key=ANTHROPIC_API_KEY), args.render, args.apply)
        return
    if not (args.content or args.source):
        parser.error("choose --content or --source: a batch never takes everything pending")
    with get_session() as session:
        ids = chosen(session, args.content, args.source)
        skipped = dropped(session, args.content or [], ids)
    for line in skipped:
        print(f"not pending: {line}")
    if args.run and skipped:
        raise SystemExit("Some chosen contents are not pending; drop them or fix them first")
    print(f"{len(ids)} pending: {ids[:20]}{' ...' if len(ids) > 20 else ''}")
    if args.run and ids:
        run(anthropic.Anthropic(api_key=ANTHROPIC_API_KEY), ids, args.scenes)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
