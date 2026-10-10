"""Score a summary on the walk rubric, which picks a walk's stops.

    python -m pipeline.walk_score               # how many are unscored, and nothing else
    python -m pipeline.walk_score --memory 42   # one, printed
    python -m pipeline.walk_score --all         # every unscored extracted memory (bills)
    python -m pipeline.walk_score --labels      # the prompt against the labels; writes nothing

One holistic question, 0-12: would a curious walker standing here be glad
they stopped to hear it? The six-criteria rubric it replaced (docs/04-extract.md)
is now the list of what raises and sinks a story; summed, its parts were
noise (docs/10, *The walk score asks one question*). It scores the finished
summary, which is what a walker reads, so the extraction prompt and its
summaries stay untouched. The Weather Girls are not in the prompt: they are
the held-out test.

Bills a little (one short model call per memory). Aggregation runs it on each
new video's memories; --all is the backfill.
"""

import argparse
import json
import logging

from sqlalchemy import text

from pipeline.config import GRADER_MODEL
from pipeline.extract import _request, image_block

logger = logging.getLogger(__name__)

PROMPT = """The text is a place, then a short story told to someone standing there.
Score it 0 to 12: would a curious walker, standing on this spot, be glad they
stopped to hear it?

What raises it: it happened right here, at this building or square; the walker
can see the spot or what is left of it; a scene with people and stakes; a
"wait, here?" surprise; awe, danger, anger, tenderness or absurdity; it changes
how the spot looks now; someone famous, introduced, was right here: this bar,
this stage, this doorway, more so on a night something happened.
What sinks it: it sells a business; a private person's death, illness or crime;
a name it never introduces; any place of its kind would tell it the same;
nothing happens, only names, dates or a description.

- 10 to 12: a story they will retell for years.
- 7 to 9: worth stopping for; they are glad they heard it here.
- 4 to 6: true and placed, but they forget it by the next corner.
- 0 to 3: nothing to stand here for."""

# The walker sees the picture beside the words (docs/10, *A picture can be the
# memory*), so its score sees it too. Text-only memories keep PROMPT as it is.
PICTURE_PROMPT = (
    PROMPT
    + """

The picture beside the text is what the walker sees with it, taken on this
spot. Score the two together: an arresting picture of the moment raises it, a
snapshot anyone could take there today sinks it."""
)

SCHEMA = {
    "type": "object",
    "properties": {"score": {"type": "integer", "enum": list(range(13))}},
    "required": ["score"],
    "additionalProperties": False,
}


def walk_score(client, summary: str, picture: str | None = None) -> int | None:
    """0-12, or None when the model did not answer usably."""
    if picture:
        user = [image_block(picture), {"type": "text", "text": summary}]
        raw = _request(client, PICTURE_PROMPT, user, SCHEMA, max_tokens=200, model=GRADER_MODEL)
    else:
        raw = _request(client, PROMPT, summary, SCHEMA, max_tokens=200, model=GRADER_MODEL)
    if raw is None:
        return None
    try:
        return min(12, max(0, int(json.loads(raw)["score"])))
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
    SELECT m.id, p.name, m.summary,
           CASE WHEN m.enrichment->'pictures'->0->>'page' = c.url
                THEN m.enrichment->'pictures'->0->>'thumb' END AS picture
    FROM memories m JOIN places p ON p.id = m.place_id
    LEFT JOIN content c ON c.id = m.content_id
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
        score = walk_score(client, f"{r.name}: {r.summary}", r.picture)
        if score is None:
            continue
        session.execute(
            text("UPDATE memories SET walk_score = :s WHERE id = :id"), {"s": score, "id": r.id}
        )
        done[r.id] = score
    return done


def auc(pos: list[int], neg: list[int]) -> float:
    """The chance a walk outscores a skip; ties count half."""
    return sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))


# Skips for reasons the summary can't show (outside the box, a bad pin, a
# duplicate, a wrong fact); other stages catch those.
UNSEEN = {"out", "pin", "p1000", "dup", "wrong", "hall"}


def check_labels(session, client, path: str = "tests/fixtures/walk_labels.json") -> dict:
    """Score the labelled memories afresh, writing nothing, and say how well the
    prompt puts walks above skips: on every label, and on the ones it can judge."""
    labels = {m["id"]: m for m in json.load(open(path))["memories"]}
    rows = session.execute(
        text(
            "SELECT m.id, p.name, m.summary FROM memories m JOIN places p ON p.id = m.place_id"
            " WHERE m.id = ANY(:ids)"
        ),
        {"ids": list(labels)},
    ).fetchall()
    scored = {r.id: walk_score(client, f"{r.name}: {r.summary}") for r in rows}
    scored = {i: s for i, s in scored.items() if s is not None}

    def split(ids):
        return (
            [scored[i] for i in ids if labels[i]["verdict"] == "walk"],
            [scored[i] for i in ids if labels[i]["verdict"] == "skip"],
        )

    seen = [i for i in scored if not set(labels[i]["flags"]) & UNSEEN]
    good = [i for i in scored if scored[i] >= 6]
    return {
        "scored": len(scored),
        "auc": round(auc(*split(scored)), 3),
        "auc_judgeable": round(auc(*split(seen)), 3),
        "good": len(good),
        "good_walks": sum(labels[i]["verdict"] == "walk" for i in good),
    }


def main():
    import anthropic

    from pipeline.config import ANTHROPIC_API_KEY
    from pipeline.db import get_session

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--memory", type=int, help="one memory, by id")
    parser.add_argument("--all", action="store_true", help="every unscored one; bills")
    parser.add_argument("--labels", action="store_true", help="measure the prompt; bills")
    args = parser.parse_args()
    with get_session() as session:
        if args.labels:
            print(check_labels(session, anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)))
            return
        if not (args.memory or args.all):
            n = len(session.execute(text(UNSCORED), {"content_id": None, "memory_id": None}).all())
            print(f"{n} unscored. --all scores them, one short model call each.")
            return
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        done = score_memories(session, client, memory_id=args.memory)
    for memory_id, score in done.items():
        print(f"{memory_id}\t{score}")
    print(f"{len(done)} scored")


if __name__ == "__main__":
    main()
