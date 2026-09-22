"""The tag vocabulary, in one place. Both writers filter against this list -
see docs/10-decisions.md#one-tag-vocabulary-not-two.
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
