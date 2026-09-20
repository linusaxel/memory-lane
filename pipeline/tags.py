"""The tag vocabulary, in one place.

There were two. The extractor's prompt listed thirteen, `api/write.py` offered
eleven for submissions, and they overlapped on six - so the app's `sport` chip
matched none of the four memories stored as `sports`, and `m.tags && …` is an
exact-string overlap. Five of the eleven offered tags matched nothing at all.

Both writers filter against this list now, which also makes the prompt's list
binding: the model was emitting `comedy`, `entertainment`, `celebrity`,
`theater` and `festival` off its own menu, because nothing checked.

Singular throughout, like every other tag - `sports` was the odd one out and
db/migrations/008_one_tag_vocabulary.sql renames it in place.
"""

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
