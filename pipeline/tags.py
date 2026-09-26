"""Tags, two ways. The extractor picks from a closed vocabulary; a person
writes #words in their description and those are the tags. See
docs/10-decisions.md#tags-come-from-the-text-and-a-walk-has-no-theme.
"""

import re

# Ordered roughly by how often the corpus uses them, because the prompt reads
# this list and order is a weak prior.
TAGS = (
    "personal",
    "travel",
    "business",
    "nightlife",
    "culture",
    "adventure",
    "comedy",
    "food",
    "drink",
    "nature",
    "music",
    "art",
    "history",
    "sport",
    "romance",
    "family",
    "work",
    "strange",
)


def clean(raw) -> list[str]:
    """Lowercased, deduplicated, and only from the vocabulary.

    Dropping an unknown tag rather than rejecting the whole thing: tags are a
    filing convenience, and losing one is not worth losing the memory.
    """
    seen = []
    for tag in raw or []:
        normalized = str(tag).strip().lower()
        if normalized in TAGS and normalized not in seen:
            seen.append(normalized)
    return seen


# `#` then letters, digits or `_`, Latin with its accents spelled out rather
# than \p{L}, so mobile/src/hashtags.ts can say exactly the same thing in
# Hermes. Not after a word character or another `#`: mail@x#y and ##x are not
# tags. tests/fixtures/hashtags.json holds both parsers to the same answers.
_WORD = "0-9A-Za-z_\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u024f"
HASHTAG = re.compile(rf"(?<![{_WORD}#])#([{_WORD}]+)")
_LETTER = re.compile("[A-Za-z\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u024f]")
MAX_HASHTAGS = 8
MAX_TAG_LENGTH = 50  # memories.tags is VARCHAR(50)[]


def from_text(text: str) -> list[str]:
    """The #words of `text`: lowercased, first use first, at most eight.
    All digits is not a tag (#1), and a word longer than the column is dropped."""
    seen: list[str] = []
    for match in HASHTAG.finditer(text or ""):
        tag = match.group(1).lower()
        if _LETTER.search(tag) and len(tag) <= MAX_TAG_LENGTH and tag not in seen:
            seen.append(tag)
    return seen[:MAX_HASHTAGS]
