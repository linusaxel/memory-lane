"""How good are the summaries, as a number.

    python -m pipeline.quality
    python -m pipeline.quality --compare new_prompt.txt [--baseline old.txt] [--sample 10] [--runs 3] [--score]
    python -m pipeline.quality --labels [tests/fixtures/walk_labels.json] [--half tune|check]
    python -m pipeline.quality --whole [5] [--runs 2]
    python -m pipeline.quality --visible [--source-type book]
    python -m pipeline.quality --places new_prompt.txt [--source-type book]

Run it before and after any prompt change; extraction costs money and you get
one shot. Baseline in docs/04-extract.md, reasoning in
docs/10-decisions.md#summary-quality-is-measured-not-asserted.

--compare runs the current prompt (or --baseline) and a candidate over the same
stable sample of transcript chunks, scores both, and prints them side by side
for a person to pick. It bills the extractor per chunk per prompt (~$0.003),
once: replies land in extraction_chunks, so a rerun, or a baseline the pipeline
already ran, is free. A chunk varies more than a prompt, so --runs N draws each
chunk N times per prompt and prints how often each keeps something. --score
also scores every kept summary on the walk rubric and checks it against its
chunk for anything the source does not say (two calls a memory, every run: a
longer summary is where invention creeps in).

--labels re-judges the stored memories the corpus read labelled walk, maybe or
skip, through the pipeline's own judge, and prints what it keeps of each. The
judge sees the place name and summary only: happened_there is not stored. It
bills the judge once per content per pass; a rerun on unchanged code is free,
so before and after a judge change only the change is paid for. --half tune
takes even content ids and --half check odd: tune a judge on one, report the other.

--visible re-judges every memory still shown from one source type, the same
way, and prints the ones the judge now drops. It hides nothing: read the list,
then `pipeline.review --reject` what should go.

--whole reads the labelled videos with the most labels as one chunk each, the
same prompt, filter and judge, and prints what it keeps beside what the
4-minute chunks kept: walks found again, failure checks, duplicates. It saves
no memory. One extractor call per video per run plus the judge, stored at
chunk_index -5, so a rerun is free; --runs draws again to show the noise.

--places judges a placement change: over the chunks of content holding an
`llm` place, the ones whose baseline keeps a memory the geocoders can't place,
it counts what each prompt keeps and how much of it the geocoders place. The
baseline is mostly read back free; the candidate bills once per chunk. The
geocoders are free and slow, about a second a memory.
"""

import argparse
import hashlib
import json
import re
import sys

import anthropic
from sqlalchemy import text

from pipeline.config import ANTHROPIC_API_KEY, GRADER_MODEL
from pipeline.db import get_session
from pipeline.extract import (
    _judge,
    _same_story,
    chunk_transcript,
    extract_chunk_stored,
    filter_low_confidence,
    merge_nearby_memories,
    place_of,
    prompt_for,
    source_context,
    unsupported,
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

# The archive's voice instead of the event: the scholar ("the manuscript gives a
# rare glimpse", "later tellings") or the planner ("the museum recommends").
SOURCE_TALK = re.compile(
    r"\b(the (manuscript|article|archive|museum|book)\b|sources?\b"
    r"|later tellings|recommend(s|ed)?\b|rare glimpse)",
    re.I,
)

WORD_LIMIT = 180

CHECKS = (
    ("anonymous subject", ANONYMOUS.search, 'says "the speaker" instead of a name'),
    ("talks about talking", META.search, "reports the recording, not the event"),
    ("not past tense", NOT_PAST.search, "an announcement or a live narration"),
    ("unnamed someone", UNNAMED.search, "the transcript usually names them"),
    ("talks about the source", SOURCE_TALK.search, "the archive's voice, not the event"),
    ("over 180 words", lambda s: len(s.split()) > WORD_LIMIT, "summarises the conversation"),
)


def score_kept(session, client, results, chunks) -> dict[str, dict]:
    """Per prompt: memories kept, mean words, mean walk score, how many add no
    fact and no colour to their chunk, and what the others added."""
    from pipeline.walk_score import walk_score

    scores = {}
    for name, per_chunk in results.items():
        words, walks, faithful, plain, added = [], [], 0, 0, []
        for (cid, i, chunk, context), runs in zip(chunks, per_chunk, strict=True):
            for m in runs[0]:
                summary = m.get("summary") or ""
                words.append(len(summary.split()))
                if (w := walk_score(client, f"{m.get('venue')}: {summary}")) is not None:
                    walks.append(w)
                extra = unsupported(session, client, cid, i, chunk, context, summary, GRADER_MODEL)
                if extra is None:
                    continue
                faithful += not any(e["kind"] == "fact" for e in extra)
                plain += not extra
                added += [f"{e['kind']}, {m.get('venue')}: {e['claim']}" for e in extra]
        n = len(words)
        scores[name] = {
            "kept": n,
            "words": sum(words) / max(n, 1),
            "walk": sum(walks) / max(len(walks), 1),
            "faithful": faithful,
            "plain": plain,
            "added": added,
        }
    return scores


def report(summaries: list[str]) -> list[tuple[str, int, str]]:
    """Pure, so it can be run against a proposed batch before it is saved."""
    return [(name, sum(1 for s in summaries if test(s)), why) for name, test, why in CHECKS]


def sample_chunks(
    session, n: int | None, source_type: str = "video", client=None, content_ids=None
) -> list[tuple]:
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
              AND (:every OR c.id = ANY(:ids))
        """),
        {"source_type": source_type, "every": content_ids is None, "ids": content_ids or []},
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


LLM_CONTENT = """
    SELECT DISTINCT m.content_id FROM memories m JOIN places p ON p.id = m.place_id
    WHERE p.geocode_status = 'llm' AND NOT m.hidden ORDER BY m.content_id
"""


def places(
    session, client, prompts: dict[str, str], source_type: str = "video"
) -> tuple[int, dict[str, tuple[int, int]]]:
    """(chunks, {prompt: (kept, placed)}) over the chunks whose first prompt
    keeps a memory the geocoders leave unplaced: the ones that make `llm` places."""
    ids = list(session.execute(text(LLM_CONTENT)).scalars())
    chunks = sample_chunks(session, None, source_type, client, ids) if ids else []
    results = compare(session, client, prompts, chunks)
    hits = {
        name: [[place_of(m) is not None for m in runs[0]] for runs in per_chunk]
        for name, per_chunk in results.items()
    }
    first = next(iter(prompts))
    keep = [i for i, placed in enumerate(hits[first]) if not all(placed)]
    return len(keep), {
        name: (sum(len(h[i]) for i in keep), sum(sum(h[i]) for i in keep))
        for name, h in hits.items()
    }


def compare(
    session, client, prompts: dict[str, str], chunks, runs: int = 1
) -> dict[str, list[list[list[dict]]]]:
    """Each prompt's kept memories, per chunk in the order of `chunks`, per run.
    Run 0 is the plain request; a later run differs only by a line in the
    context, as in read_whole, so it is a fresh draw that is also stored."""
    return {
        name: [
            [
                filter_low_confidence(
                    extract_chunk_stored(
                        session,
                        client,
                        cid,
                        i,
                        chunk,
                        prompt,
                        context + (f"\n(read {run})" if run else ""),
                    )
                )
                for run in range(runs)
            ]
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
    for n, (content_id, group) in enumerate(by_content.items(), 1):
        print(f"content {n}/{len(by_content)}", file=sys.stderr)
        memories = [{"id": r.id, "venue": r.name, "summary": r.summary} for r in group]
        survivors = {m["id"] for m in worth_telling(session, client, content_id, memories)}
        kept |= {m["id"]: m["id"] in survivors for m in memories}
        # The first pass, read back from extraction_chunks if it succeeded.
        if _judge(session, client, content_id, memories, list(range(len(memories)))) is None:
            failed.append(content_id)
    return kept, failed


def visible(session, source_type: str) -> list:
    """(id, place, summary) of every memory still shown from this source type."""
    return session.execute(
        text("""
            SELECT m.id, p.name AS place, m.summary
            FROM memories m
            JOIN places p ON p.id = m.place_id
            JOIN content c ON c.id = m.content_id
            WHERE NOT m.hidden AND COALESCE(c.source_type, 'video') = :source_type
            ORDER BY m.id
        """),
        {"source_type": source_type},
    ).fetchall()


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


# A whole video's memories at once; 2000 tokens holds about six.
WHOLE_INDEX = -5
WHOLE_MAX_TOKENS = 16000


def labelled_videos(session, labels: list[dict], n: int) -> list:
    """The n video contents with the most labelled memories, each with its
    labelled memories as {id, verdict, venue, summary}."""
    verdict = {m["id"]: m["verdict"] for m in labels}
    rows = session.execute(
        text("""
            SELECT m.content_id, m.id, p.name, m.summary
            FROM memories m
            JOIN places p ON p.id = m.place_id
            JOIN content c ON c.id = m.content_id
            WHERE m.id = ANY(:ids) AND COALESCE(c.source_type, 'video') = 'video'
            ORDER BY m.id
        """),
        {"ids": list(verdict)},
    ).fetchall()
    by_content: dict[int, list] = {}
    for r in rows:
        by_content.setdefault(r.content_id, []).append(
            {"id": r.id, "verdict": verdict[r.id], "venue": r.name, "summary": r.summary}
        )
    return sorted(by_content.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:n]


def read_whole(session, client, content_id: int, run: int = 0) -> list[dict]:
    """One video as one chunk, through the pipeline's merge, filter and judge.
    Saves nothing. Run 0 is the plain request; a later run differs only by a
    line in the context, so it is a fresh draw that is also stored."""
    r = session.execute(
        text("""
            SELECT c.title, c.source_name, t.segments
            FROM content c JOIN transcripts t ON t.content_id = c.id WHERE c.id = :id
        """),
        {"id": content_id},
    ).one()
    segments = r.segments if isinstance(r.segments, list) else json.loads(r.segments)
    whole = "\n".join(chunk_transcript(segments, chunk_minutes=10**6))
    brief = video_brief(session, client, content_id, segments, r.source_name, r.title)
    context = source_context(r.source_name, r.title, brief) + (f"\n(read {run})" if run else "")
    memories = extract_chunk_stored(
        session,
        client,
        content_id,
        WHOLE_INDEX,
        whole,
        prompt_for("video"),
        context,
        max_tokens=WHOLE_MAX_TOKENS,
    )
    kept = filter_low_confidence(merge_nearby_memories(memories))
    return worth_telling(session, client, content_id, kept)


def found(labelled: dict, memories: list[dict]) -> bool:
    """A labelled memory is found again by its venue or its story."""
    place = (labelled["venue"] or "").split(",")[0].strip().lower()
    return any(
        ((v := (m.get("venue") or "").strip().lower()) and (v in place or place in v))
        or _same_story(labelled, m)
        for m in memories
    )


def duplicates(memories: list[dict]) -> int:
    """Pairs that tell one story, whatever venue each names."""
    return sum(_same_story(a, b) for i, a in enumerate(memories) for b in memories[i + 1 :])


def score_whole(labelled: list[dict], memories: list[dict]) -> dict:
    """Pure: walks found again, failure checks and duplicates, both sides."""
    walks = [m for m in labelled if m["verdict"] == "walk"]

    def side(ms):
        s = [m.get("summary") or "" for m in ms]
        return {
            "kept": len(ms),
            "checks": dict((n, c) for n, c, _ in report(s)),
            "dups": duplicates(ms),
        }

    return {
        "walks": len(walks),
        "walks_found": sum(found(w, memories) for w in walks),
        "chunked": side(labelled),
        "whole": side(memories),
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


def _print_comparison(results: dict[str, list[list[list[dict]]]], chunks):
    for name, per_chunk in results.items():
        print(f"\n== {name}")
        kept = [m for runs in per_chunk for m in runs[0]]
        _print_report([m.get("summary") or "" for m in kept])
        print(f"{'with a quote':<22}{sum(1 for m in kept if m.get('quote')):>5}")

    for n, (cid, i, _, _) in enumerate(chunks):
        print(f"\n--- content {cid} chunk {i}")
        for name, per_chunk in results.items():
            runs = per_chunk[n]
            print(f"  {name}: keeps something in {sum(map(bool, runs))}/{len(runs)} runs")
            for m in runs[0] or [{"venue": "(nothing)", "summary": ""}]:
                print(f"    {m.get('venue')}: {m.get('summary')}")
                if m.get("quote"):
                    print(f'      "{m["quote"]}" - {m.get("quote_by") or "?"}')


def _print_whole(results):
    for content_id, labelled, runs in results:
        print(f"\n=== content {content_id}")
        for run, memories in enumerate(runs):
            sc = score_whole(labelled, memories)
            print(f"  run {run}: walks found {sc['walks_found']}/{sc['walks']}")
            for name in ("chunked", "whole"):
                side = sc[name]
                bad = {k: v for k, v in side["checks"].items() if v}
                print(f"    {name:<8} kept {side['kept']:>3}  dups {side['dups']}  {bad or ''}")
        print("  chunked (labelled):")
        for m in labelled:
            print(f"    [{m['verdict']}] {m['venue']}: {m['summary']}")
        for run, memories in enumerate(runs):
            print(f"  whole, run {run}:")
            for m in memories or [{"venue": "(nothing)", "summary": ""}]:
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
    parser.add_argument(
        "--visible", action="store_true", help="re-judge what --source-type shows now"
    )
    parser.add_argument("--whole", nargs="?", type=int, const=5, metavar="VIDEOS")
    parser.add_argument("--runs", type=int, default=1, help="draws per chunk (--compare, --whole)")
    parser.add_argument("--places", metavar="PROMPT_FILE", help="a candidate placement prompt")
    parser.add_argument(
        "--score", action="store_true", help="--compare: walk rubric and faithfulness (bills)"
    )
    args = parser.parse_args()

    if args.places:
        with open(args.places) as f:
            candidate = f.read()
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        prompts = {"baseline": prompt_for(args.source_type), "candidate": candidate}
        with get_session() as session:
            n, counts = places(session, client, prompts, args.source_type)
        print(f"{n} chunks that make an llm place")
        for name, (kept, placed) in counts.items():
            print(f"{name}: placed {placed} of {kept} kept")
        return

    if args.whole:
        with open("tests/fixtures/walk_labels.json") as f:
            labels = json.load(f)["memories"]
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        with get_session() as session:
            results = [
                (cid, labelled, [read_whole(session, client, cid, r) for r in range(args.runs)])
                for cid, labelled in labelled_videos(session, labels, args.whole)
            ]
        _print_whole(results)
        return

    if args.visible:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        with get_session() as session:
            rows = visible(session, args.source_type)
            kept, failed = replay_labels(session, client, [r.id for r in rows])
        if failed:
            raise SystemExit(f"the judge failed on contents {failed}: no verdict")
        dropped = [r for r in rows if not kept[r.id]]
        print(f"dropped {len(dropped)} of {len(rows)}")
        for r in dropped:
            print(f"\n{r.id}  {r.place}\n  {r.summary}")
        return

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
                session, client, {"baseline": baseline, "candidate": candidate}, chunks, args.runs
            )
            scores = score_kept(session, client, results, chunks) if args.score else {}
        _print_comparison(results, chunks)
        if scores:
            for name, s in scores.items():
                print(
                    f"\n== {name} scored: kept {s['kept']}, {s['words']:.0f} words, "
                    f"walk {s['walk']:.1f}/12, no added fact {s['faithful']}/{s['kept']}, "
                    f"nothing added {s['plain']}/{s['kept']}"
                )
                for a in s["added"]:
                    print(f"  added: {a}")
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
