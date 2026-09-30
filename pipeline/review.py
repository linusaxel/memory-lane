"""Review extracted memories by hand; the verdicts are the known-good set.

    python -m pipeline.review                          # the next 20 unreviewed
    python -m pipeline.review --accept 12,13 --reject 14
    python -m pipeline.review --edit 15 "Mark and Joe got thrown out of Katz's."
    python -m pipeline.review --stats                  # edit rate by extraction month
    python -m pipeline.review --flagged                # only claims the chunk doesn't make
    python -m pipeline.review --check                  # list those claims for older memories

Accepted is a positive, rejected a negative (and hidden from every endpoint),
and edited a before/after pair. The share of reviews that needed an edit or a
reject is the quality number: pipeline/quality.py's regexes are the cheap first
pass, this is what a person actually changed. Reviews outlive the memory they
judge, so reprocessing a video does not throw them away. A later accept does
not un-hide a reject: `hidden` is shared with reports, and this cannot tell
which one set it.

A memory shows the claims its chunk doesn't make, found by extraction or by
--check. They are for a person to judge with --edit; nothing corrects them
(docs/10-decisions.md#a-summary-is-checked-against-its-chunk-not-corrected).
--check bills one Sonnet call per chunk not checked before.
"""

import argparse
import json

import anthropic
from sqlalchemy import text

from pipeline.config import ANTHROPIC_API_KEY, CHUNK_MINUTES, CHUNK_OVERLAP_SECONDS
from pipeline.db import get_session
from pipeline.extract import chunk_transcript, source_context, unsupported, video_brief
from pipeline.quality import CHECKS


def unreviewed(session, limit: int, flagged: bool = False):
    return session.execute(
        text("""
            SELECT m.id, p.name, m.summary, m.unsupported
            FROM memories m
            JOIN places p ON p.id = m.place_id
            LEFT JOIN memory_reviews r ON r.memory_id = m.id
            WHERE m.content_id IS NOT NULL AND NOT m.hidden AND r.id IS NULL
              AND (NOT :flagged OR cardinality(m.unsupported) > 0)
            ORDER BY m.id
            LIMIT :n
        """),
        {"n": limit, "flagged": flagged},
    ).fetchall()


def check(session, client) -> int:
    """List the unsupported claims of visible memories never checked, each
    against the chunk that wrote it: extraction_chunks holds that reply, with
    the summary verbatim. A summary edited since matches no reply and is left.
    Returns how many were checked."""
    todo = session.execute(
        text("""
            SELECT m.id, m.content_id, m.summary FROM memories m
            WHERE m.content_id IS NOT NULL AND NOT m.hidden AND m.unsupported IS NULL
            ORDER BY m.content_id, m.id
        """)
    ).fetchall()
    by_content: dict[int, list] = {}
    for m in todo:
        by_content.setdefault(m.content_id, []).append(m)
    checked = 0
    for content_id, mems in by_content.items():
        chunk_of = {}
        for r in session.execute(
            text("""
                SELECT chunk_index, response FROM extraction_chunks
                WHERE content_id = :c AND chunk_index >= 0
            """),
            {"c": content_id},
        ):
            try:
                for m in json.loads(r.response).get("memories", []):
                    chunk_of[(m.get("summary") or "").strip()] = r.chunk_index
            except (ValueError, AttributeError):
                continue
        c = session.execute(
            text("""
                SELECT c.title, c.source_name, c.source_type, t.segments
                FROM content c JOIN transcripts t ON t.content_id = c.id WHERE c.id = :c
            """),
            {"c": content_id},
        ).fetchone()
        if c is None:
            continue
        segments = c.segments if isinstance(c.segments, list) else json.loads(c.segments)
        chunks = chunk_transcript(segments, CHUNK_MINUTES, CHUNK_OVERLAP_SECONDS)
        brief = ""
        if (c.source_type or "video") == "video":
            brief = video_brief(session, client, content_id, segments, c.source_name, c.title)
        context = source_context(c.source_name, c.title, brief)
        by_chunk: dict[int, list] = {}
        for m in mems:
            i = chunk_of.get(m.summary.strip())
            if i is not None and i < len(chunks):
                by_chunk.setdefault(i, []).append(m)
        for i, group in by_chunk.items():
            memories = [{"summary": m.summary} for m in group]
            claims = unsupported(session, client, content_id, i, chunks[i], context, memories)
            if claims is None:
                continue
            for m, found in zip(group, claims, strict=True):
                session.execute(
                    text("UPDATE memories SET unsupported = :u WHERE id = :id"),
                    {"u": found, "id": m.id},
                )
                checked += 1
            session.commit()
    return checked


def review(session, memory_id: int, verdict: str, after: str | None = None):
    """Record one verdict. A second review of the same memory replaces the
    verdict but keeps the original `before`: that is the model's own text."""
    row = session.execute(
        text("SELECT content_id, summary, created_at FROM memories WHERE id = :id"),
        {"id": memory_id},
    ).fetchone()
    if row is None or row.content_id is None:
        raise SystemExit(f"memory {memory_id}: no such extracted memory")

    session.execute(
        text("""
            INSERT INTO memory_reviews
                (memory_id, content_id, verdict, before, after, extracted_at)
            VALUES (:id, :content_id, :verdict, :before, :after, :extracted_at)
            ON CONFLICT (memory_id) DO UPDATE SET
                verdict = EXCLUDED.verdict,
                after = EXCLUDED.after,
                reviewed_at = CURRENT_TIMESTAMP
        """),
        {
            "id": memory_id,
            "content_id": row.content_id,
            "verdict": verdict,
            "before": row.summary,
            "after": after,
            "extracted_at": row.created_at,
        },
    )
    if verdict == "edit":
        session.execute(
            text("UPDATE memories SET summary = :s WHERE id = :id"), {"s": after, "id": memory_id}
        )
    elif verdict == "reject":
        session.execute(text("UPDATE memories SET hidden = TRUE WHERE id = :id"), {"id": memory_id})


def stats(session):
    return session.execute(
        text("""
            SELECT to_char(extracted_at, 'YYYY-MM') AS month,
                   COUNT(*) AS reviewed,
                   COUNT(*) FILTER (WHERE verdict = 'accept') AS accepted,
                   COUNT(*) FILTER (WHERE verdict = 'edit') AS edited,
                   COUNT(*) FILTER (WHERE verdict = 'reject') AS rejected
            FROM memory_reviews
            GROUP BY 1
            ORDER BY 1
        """)
    ).fetchall()


def _ids(spec: str) -> list[int]:
    try:
        return [int(x) for x in spec.split(",") if x.strip()]
    except ValueError:
        raise SystemExit(f"expected comma-separated memory ids, got {spec!r}") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accept", metavar="ID,...", default="")
    parser.add_argument("--reject", metavar="ID,...", default="")
    parser.add_argument("--edit", nargs=2, action="append", metavar=("ID", "SUMMARY"), default=[])
    parser.add_argument("--stats", action="store_true")
    parser.add_argument("--flagged", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    with get_session() as session:
        if args.check:
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            print(f"{check(session, client)} memories checked")
            return
        if args.stats:
            for r in stats(session):
                changed = (r.edited + r.rejected) * 100 // r.reviewed
                print(
                    f"{r.month or 'unknown'}  {r.reviewed:>4} reviewed  "
                    f"{r.accepted:>4} ok  {r.edited:>4} edited  {r.rejected:>4} rejected  "
                    f"{changed}% changed"
                )
            return

        decided = [(i, "accept", None) for i in _ids(args.accept)]
        decided += [(i, "reject", None) for i in _ids(args.reject)]
        decided += [(_ids(i)[0], "edit", s) for i, s in args.edit]
        for memory_id, verdict, after in decided:
            review(session, memory_id, verdict, after)
        if decided:
            print(f"{len(decided)} reviews recorded")
            return

        for r in unreviewed(session, args.limit, args.flagged):
            flags = [name for name, test, _ in CHECKS if test(r.summary)]
            print(f"[{r.id}] {r.name}" + (f"  ({', '.join(flags)})" if flags else ""))
            print(f"  {r.summary}")
            for claim in r.unsupported or []:
                print(f"  ? {claim}")
            print()


if __name__ == "__main__":
    main()
