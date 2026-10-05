"""Public-domain books scanned by the Internet Archive, read from their OCR text.

The query is the item identifier, optionally followed by a word, as for
Gutenberg: "desvandtdesvandt00bokk" or "kjbenhavnshisto04nielgoog Amagertorv".
The OCR breaks words across lines with a hyphen, which is mended before the
text is cut into windows. docs/10, *The sources' legal footing*.
"""

import json
import re

from crawler.gutenberg import download, windows

META = "https://archive.org/metadata/{id}/metadata"
TEXT = "https://archive.org/download/{id}/{id}_djvu.txt"
LANGUAGES = {"dan": "da", "eng": "en", "ger": "de", "fre": "fr"}


def mend(raw: str) -> str:
    """Join the words the OCR split across a line: "Kre-\\naturer" is "Kreaturer"."""
    return re.sub(r"(\w)- *\n(\w)", r"\1\2", raw)


class Archive:
    name = "archive"
    source_name = "Internet Archive"
    source_type = "book"

    def fetch(self, query: str, limit: int):
        item, _, word = query.partition(" ")
        meta = json.loads(download(META.format(id=item))).get("result", {})
        title = meta.get("title") or item
        language = LANGUAGES.get(meta.get("language", ""), "da")
        text = mend(download(TEXT.format(id=item)).decode("utf-8", "replace"))
        for n, chunk in enumerate(windows(text, word.strip() or None)[:limit], 1):
            yield {
                "source_url": f"https://archive.org/details/{item}#{n}",
                "title": f"{title}, part {n}",
                "text": chunk,
                "language": language,
            }
