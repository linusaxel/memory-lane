"""How good are the summaries, as a number.

    python -m pipeline.quality

Run it before and after any prompt change; extraction costs money and you get
one shot. Baseline in CLAUDE.md, reasoning in
docs/10-decisions.md#summary-quality-is-measured-not-asserted.
"""

import re

from sqlalchemy import text

from pipeline.db import get_session

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


def main():
    with get_session() as session:
        summaries = [r[0] for r in session.execute(text("SELECT summary FROM memories")) if r[0]]

    total = len(summaries)
    if not total:
        print("no memories")
        return

    print(f"{'total':<22}{total:>5}")
    for name, count, why in report(summaries):
        print(f"{name:<22}{count:>5}  ({count * 100 // total}%)   {why}")

    worst = max(summaries, key=lambda s: len(s.split()))
    print(f"\nlongest: {len(worst.split())} words\n  {worst[:160]}...")


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    main()
