"""Is this fit to show a stranger? App Store 1.2 wants a filter on what people
post, before anybody else reads it.

Local rules, no network: a word list, contact details and links. A hit is 422
and says so; the rest is published, and reports, the threshold and blocking
catch what the rules miss. docs/10-decisions.md#posts-are-screened-by-rules-not-a-model.
"""

import pathlib
import re
import unicodedata

from fastapi import HTTPException

WORDS = [
    line
    for line in (pathlib.Path(__file__).parent / "blocked_words.txt").read_text().splitlines()
    if line and not line.startswith("#")
]
BLOCKED = re.compile(r"(?<!\w)(" + "|".join(re.escape(w) for w in WORDS) + r")(?!\w)")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
LINK = re.compile(r"https?://|www\.")
# A run of digits and the separators a phone number is written with.
PHONE = re.compile(r"\+?\(?\d[\d\s().-]{6,}\d")
# Two years joined, "1978-1985": a run with eight digits that is not a number.
YEARS = re.compile(r"\d{4}\s*[-–]\s*\d{4}")


def _phone(text: str) -> bool:
    return any(
        sum(c.isdigit() for c in run) >= 8 and not YEARS.fullmatch(run.strip())
        for run in PHONE.findall(text)
    )


def refused(text: str) -> bool:
    text = unicodedata.normalize("NFKC", text).lower()
    return bool(BLOCKED.search(text) or EMAIL.search(text) or LINK.search(text) or _phone(text))


def screen(*texts: str | None) -> None:
    """Return if it may be shown; raise 422 if it may not."""
    if any(t and refused(t) for t in texts):
        raise HTTPException(status_code=422, detail={"reason": "refused"})
