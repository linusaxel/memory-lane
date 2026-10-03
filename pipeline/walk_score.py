"""Score a summary on the walk rubric, which decides what is epic.

    python -m pipeline.walk_score               # how many are unscored, and nothing else
    python -m pipeline.walk_score --memory 42   # one, printed
    python -m pipeline.walk_score --all         # every unscored extracted memory (bills)

The rubric is docs/04-extract.md's research rubric: six criteria, 0-2 each.
It scores the finished summary, which is what a walker reads, so the
extraction prompt and its summaries stay untouched. The Weather Girls are not
in the prompt: they are the held-out test.

Bills a little (one short model call per memory). Aggregation runs it on each
new video's memories; --all is the backfill.
"""

import argparse
import json
import logging

from sqlalchemy import text

from pipeline.extract import _request

logger = logging.getLogger(__name__)

CRITERIA = ("site_lock", "visible_trace", "incident", "surprise", "feeling", "relates")

PROMPT = """The text is a short story told to someone standing at a place. Score it
on six criteria, each 0, 1 or 2:

- site_lock: 2 if it happened at this doorway, 0 if only "in the city".
- visible_trace: 2 if it points at something still there to look at.
- incident: 2 for a scene with people and stakes, 0 for names and dates.
- surprise: 2 for a "wait, here?", a small gap the reader wants closed.
- feeling: 2 for awe, danger, anger or absurdity.
- relates: 2 if then is set against now, tied to the person standing there.

Be strict: a 2 is rare. Most stories total 5 to 8."""

SCHEMA = {
    "type": "object",
    "properties": {c: {"type": "integer", "enum": [0, 1, 2]} for c in CRITERIA},
    "required": list(CRITERIA),
    "additionalProperties": False,
}


def walk_score(client, summary: str) -> int | None:
    """0-12, or None when the model did not answer usably."""
    raw = _request(client, PROMPT, summary, SCHEMA, max_tokens=200)
    if raw is None:
        return None
    try:
        scores = json.loads(raw)
        return sum(min(2, max(0, int(scores[c]))) for c in CRITERIA)
    except (
        ValueError,
        KeyError,
        TypeError,
    ):
        # Kept exploded with a trailing comma on purpose.
        # See docs/10-decisions.md#except-a-b-stays-exploded
        logger.warning("Unusable walk score: %s", raw[:200])
        return None


UNSCORED = """
    SELECT m.id, m.summary FROM memories m
    WHERE m.walk_score IS NULL AND m.user_id IS NULL
      AND (CAST(:content_id AS INTEGER) IS NULL OR m.content_id = :content_id)
      AND (CAST(:memory_id AS INTEGER) IS NULL OR m.id = :memory_id)
    ORDER BY m.id
"""


def score_memories(session, client, content_id: int | None = None, memory_id: int | None = None):
    """Score every extracted memory still unscored; return {memory_id: score}.
    Only extracted ones: what a person filed is theirs, and hearts decide it."""
    rows = session.execute(
        text(UNSCORED), {"content_id": content_id, "memory_id": memory_id}
    ).fetchall()
    done = {}
    for r in rows:
        score = walk_score(client, r.summary)
        if score is None:
            continue
        session.execute(
            text("UPDATE memories SET walk_score = :s WHERE id = :id"), {"s": score, "id": r.id}
        )
        done[r.id] = score
    return done


def main():
    import anthropic

    from pipeline.config import ANTHROPIC_API_KEY
    from pipeline.db import get_session

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--memory", type=int, help="one memory, by id")
    parser.add_argument("--all", action="store_true", help="every unscored one; bills")
    args = parser.parse_args()
    with get_session() as session:
        if not (args.memory or args.all):
            n = len(session.execute(text(UNSCORED), {"content_id": None, "memory_id": None}).all())
            print(f"{n} unscored. --all scores them, one short model call each.")
            return
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        done = score_memories(session, client, memory_id=args.memory)
    for memory_id, score in done.items():
        print(f"{memory_id}\t{score}")
    print(f"{len(done)} scored, {sum(s >= 11 for s in done.values())} epic by score")


if __name__ == "__main__":
    main()
