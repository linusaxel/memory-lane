"""How good are the summaries, as a number.

    python -m pipeline.quality
    python -m pipeline.quality --compare new_prompt.txt [--baseline old.txt] [--sample 10]

Run it before and after any prompt change; extraction costs money and you get
one shot. Baseline in docs/04-extract.md, reasoning in
docs/10-decisions.md#summary-quality-is-measured-not-asserted.

--compare runs the current prompt (or --baseline) and a candidate over the same
stable sample of transcript chunks, scores both, and prints them side by side
for a person to pick. It bills the extractor per chunk per prompt (~$0.003),
once: replies land in extraction_chunks, so a rerun, or a baseline the pipeline
already ran, is free.
"""

import argparse
import hashlib
import json
import re

import anthropic
from sqlalchemy import text

from pipeline.config import ANTHROPIC_API_KEY
from pipeline.db import get_session
from pipeline.extract import (
    chunk_transcript,
    extract_chunk_stored,
    filter_low_confidence,
    prompt_for,
    source_context,
)

# The label instead of the name. This is the big one, and the prompt now bans it.
ANONYMOUS = re.compile(r"\bthe (speakers?|hosts?|comedians?|narrators?)\b", re.I)

# Reporting the recording rather than the event. "He describes" is a summary of a
# conversation; the person standing there wants the thing that happened.
META = re.compile(
    r"\b(mention(s|ed)?|describ(es|ed)|discuss(es|ed|ing)?|talk(s|ed|ing)? about"
    r"|recount(s|ed)?|explain(s|ed)|not(es|ed) that|says? that)\b",
    re.I,
)

# Present or future: an announcement, not a memory. "is performing", "will be".
NOT_PAST = re.compile(
    r"\b(is|are|'s|'re) (going to |about to )?\w+ing\b|\bwill be\b|\bupcoming\b", re.I
)

WORD_LIMIT = 70

CHECKS = (
    ("anonymous subject", ANONYMOUS.search, 'says "the speaker" instead of a name'),
    ("talks about talking", META.search, "reports the recording, not the event"),
    ("not past tense", NOT_PAST.search, "an announcement or a live narration"),
    ("over 70 words", lambda s: len(s.split()) > WORD_LIMIT, "summarises the conversation"),
)


def report(summaries: list[str]) -> list[tuple[str, int, str]]:
    """Pure, so it can be run against a proposed batch before it is saved."""
    return [(name, sum(1 for s in summaries if test(s)), why) for name, test, why in CHECKS]


def sample_chunks(session, n: int, source_type: str = "video") -> list[tuple]:
    """(content_id, chunk_index, chunk, context), the same n every run.

    Rebuilt from transcripts rather than read from anywhere extraction wrote,
    so it works whichever path extracted the video, and the chunk text and
    context come out identical to the pipeline's - which is what lets a
    baseline the pipeline already paid for be read back for free.
    """
    rows = session.execute(
        text("""
            SELECT c.id, c.title, c.source_name, t.segments
            FROM content c
            JOIN transcripts t ON t.content_id = c.id
            WHERE COALESCE(c.source_type, 'video') = :source_type
        """),
        {"source_type": source_type},
    ).fetchall()
    chunks = []
    for r in rows:
        segments = r.segments if isinstance(r.segments, list) else json.loads(r.segments)
        context = source_context(r.source_name, r.title)
        chunks += [(r.id, i, c, context) for i, c in enumerate(chunk_transcript(segments))]
    chunks.sort(key=lambda c: hashlib.md5(f"{c[0]}-{c[1]}".encode()).hexdigest())
    return chunks[:n]


def compare(session, client, prompts: dict[str, str], chunks) -> dict[str, list[list[dict]]]:
    """Each prompt's kept memories, per chunk, in the order of `chunks`."""
    return {
        name: [
            filter_low_confidence(
                extract_chunk_stored(session, client, cid, i, chunk, prompt, context)
            )
            for cid, i, chunk, context in chunks
        ]
        for name, prompt in prompts.items()
    }


def _print_report(summaries: list[str]):
    total = len(summaries)
    print(f"{'total':<22}{total:>5}")
    for name, count, why in report(summaries):
        print(f"{name:<22}{count:>5}  ({count * 100 // max(total, 1)}%)   {why}")


def _print_comparison(results: dict[str, list[list[dict]]], chunks):
    for name, per_chunk in results.items():
        print(f"\n== {name}")
        _print_report([m.get("summary") or "" for kept in per_chunk for m in kept])

    for n, (cid, i, _, _) in enumerate(chunks):
        print(f"\n--- content {cid} chunk {i}")
        for name, per_chunk in results.items():
            print(f"  {name}:")
            for m in per_chunk[n] or [{"venue": "(nothing)", "summary": ""}]:
                print(f"    {m.get('venue')}: {m.get('summary')}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compare", metavar="PROMPT_FILE", help="a candidate system prompt")
    parser.add_argument("--baseline", metavar="PROMPT_FILE", help="default: the current prompt")
    parser.add_argument("--sample", type=int, default=10)
    parser.add_argument("--source-type", default="video")
    args = parser.parse_args()

    if args.compare:
        with open(args.compare) as f:
            candidate = f.read()
        if args.baseline:
            with open(args.baseline) as f:
                baseline = f.read()
        else:
            baseline = prompt_for(args.source_type)
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        with get_session() as session:
            chunks = sample_chunks(session, args.sample, args.source_type)
            results = compare(
                session, client, {"baseline": baseline, "candidate": candidate}, chunks
            )
        _print_comparison(results, chunks)
        return

    with get_session() as session:
        summaries = [r[0] for r in session.execute(text("SELECT summary FROM memories")) if r[0]]

    if not summaries:
        print("no memories")
        return

    _print_report(summaries)

    worst = max(summaries, key=lambda s: len(s.split()))
    print(f"\nlongest: {len(worst.split())} words\n  {worst[:160]}...")


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    main()
