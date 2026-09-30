"""How good are the summaries, as a number.

    python -m pipeline.quality
    python -m pipeline.quality --compare new_prompt.txt [--baseline old.txt] [--sample 10]
    python -m pipeline.quality --labels [tests/fixtures/walk_labels.json] [--half tune|check]

Run it before and after any prompt change; extraction costs money and you get
one shot. Baseline in docs/04-extract.md, reasoning in
docs/10-decisions.md#summary-quality-is-measured-not-asserted.

--compare runs the current prompt (or --baseline) and a candidate over the same
stable sample of transcript chunks, scores both, and prints them side by side
for a person to pick. It bills the extractor per chunk per prompt (~$0.003),
once: replies land in extraction_chunks, so a rerun, or a baseline the pipeline
already ran, is free.

--labels re-judges the stored memories the corpus read labelled walk, maybe or
skip, through the pipeline's own judge, and prints what it keeps of each. The
judge sees the place name and summary only: happened_there is not stored. It
bills the judge once per content per pass; a rerun on unchanged code is free,
so before and after a judge change only the change is paid for. --half tune
takes even content ids and --half check odd: tune a judge on one, report the other.
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
    _judge,
    chunk_transcript,
    extract_chunk_stored,
    filter_low_confidence,
    prompt_for,
    source_context,
    video_brief,
    worth_telling,
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

# Nobody, when the video usually names the person, or at least their nickname.
UNNAMED = re.compile(r"\bsomeone\b", re.I)

WORD_LIMIT = 70

CHECKS = (
    ("anonymous subject", ANONYMOUS.search, 'says "the speaker" instead of a name'),
    ("talks about talking", META.search, "reports the recording, not the event"),
    ("not past tense", NOT_PAST.search, "an announcement or a live narration"),
    ("unnamed someone", UNNAMED.search, "the transcript usually names them"),
    ("over 70 words", lambda s: len(s.split()) > WORD_LIMIT, "summarises the conversation"),
)


def report(summaries: list[str]) -> list[tuple[str, int, str]]:
    """Pure, so it can be run against a proposed batch before it is saved."""
    return [(name, sum(1 for s in summaries if test(s)), why) for name, test, why in CHECKS]


def sample_chunks(session, n: int, source_type: str = "video", client=None) -> list[tuple]:
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
        chunks += [(r.id, i, c, segments, r) for i, c in enumerate(chunk_transcript(segments))]
    chunks.sort(key=lambda c: hashlib.md5(f"{c[0]}-{c[1]}".encode()).hexdigest())
    # The brief is built only for the videos sampled: it is one billed call each.
    brief = client is not None and source_type == "video"
    return [
        (
            cid,
            i,
            c,
            source_context(
                r.source_name,
                r.title,
                video_brief(session, client, cid, segs, r.source_name, r.title) if brief else "",
            ),
        )
        for cid, i, c, segs, r in chunks[:n]
    ]


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


def replay_labels(session, client, ids, half=None) -> tuple[dict[int, bool], list[int]]:
    """({memory_id: kept}, contents the judge failed on) for the labelled
    memories still in the database, judged together per content as the
    pipeline judges a video. half 0 or 1 takes the contents of that parity.

    A failed judge keeps everything, which would score as a lenient judge, so
    the failures are returned for the caller to refuse."""
    rows = session.execute(
        text("""
            SELECT m.id, m.content_id, p.name, m.summary
            FROM memories m JOIN places p ON p.id = m.place_id
            WHERE m.id = ANY(:ids) AND (CAST(:half AS int) IS NULL OR m.content_id % 2 = :half)
            ORDER BY m.content_id, m.id
        """),
        {"ids": list(ids), "half": half},
    ).fetchall()
    by_content: dict[int, list] = {}
    for r in rows:
        by_content.setdefault(r.content_id, []).append(r)
    kept, failed = {}, []
    for content_id, group in by_content.items():
        memories = [{"id": r.id, "venue": r.name, "summary": r.summary} for r in group]
        survivors = {m["id"] for m in worth_telling(session, client, content_id, memories)}
        kept |= {m["id"]: m["id"] in survivors for m in memories}
        # The first pass, read back from extraction_chunks if it succeeded.
        if _judge(session, client, content_id, memories, list(range(len(memories)))) is None:
            failed.append(content_id)
    return kept, failed


def score_labels(kept: dict[int, bool], labels: list[dict]) -> dict:
    """Kept per verdict and per flag, precision and walk recall. Pure."""
    judged = [m for m in labels if m["id"] in kept]
    verdicts = {v: [0, 0] for v in ("walk", "maybe", "skip")}
    flags: dict[str, list[int]] = {}
    for m in judged:
        verdicts[m["verdict"]][kept[m["id"]]] += 1
        for f in m["flags"]:
            flags.setdefault(f, [0, 0])[kept[m["id"]]] += 1
    n_kept = sum(kept[m["id"]] for m in judged)
    walk_kept, walk_dropped = verdicts["walk"][1], verdicts["walk"][0]
    return {
        "missing": len(labels) - len(judged),
        "verdicts": verdicts,
        "flags": flags,
        "precision": walk_kept / n_kept if n_kept else 0.0,
        "recall": walk_kept / (walk_kept + walk_dropped) if walk_kept + walk_dropped else 0.0,
    }


def _print_labels(score: dict):
    print(f"{'':<10}{'kept':>6}{'dropped':>9}")
    for v, (dropped, kept) in score["verdicts"].items():
        print(f"{v:<10}{kept:>6}{dropped:>9}")
    print(f"\nprecision {score['precision']:.0%} (walk of kept)")
    print(f"recall    {score['recall']:.0%} (kept of walk)")
    print(f"\n{'flag':<10}{'kept':>6}{'dropped':>9}")
    for f, (dropped, kept) in sorted(score["flags"].items(), key=lambda x: -sum(x[1])):
        print(f"{f:<10}{kept:>6}{dropped:>9}")
    if score["missing"]:
        print(f"\n{score['missing']} labelled memories are not in this database")


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
    parser.add_argument(
        "--labels", nargs="?", const="tests/fixtures/walk_labels.json", metavar="LABELS_FILE"
    )
    parser.add_argument(
        "--half", choices=("tune", "check"), help="--labels on even or odd content ids only"
    )
    args = parser.parse_args()

    if args.labels:
        with open(args.labels) as f:
            labels = json.load(f)["memories"]
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        half = {"tune": 0, "check": 1}.get(args.half)
        with get_session() as session:
            kept, failed = replay_labels(session, client, [m["id"] for m in labels], half)
        if failed:
            raise SystemExit(f"the judge failed on contents {failed}: no score")
        if half is not None:
            labels = [m for m in labels if m["id"] in kept]
        _print_labels(score_labels(kept, labels))
        return

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
            chunks = sample_chunks(session, args.sample, args.source_type, client)
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
