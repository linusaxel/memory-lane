"""Public-domain books scanned by the Internet Archive, read from their OCR text.

The query is the item identifier, optionally followed by a word, as for
Gutenberg: "desvandtdesvandt00bokk" or "kjbenhavnshisto04nielgoog Amagertorv".
The OCR breaks words across lines with a hyphen, which is mended before the
text is cut into windows. docs/10, *The sources' legal footing*.
"""

import json
import re
from urllib.parse import quote

from crawler.gutenberg import download, windows

META = "https://archive.org/metadata/{id}"
TEXT = "https://archive.org/download/{id}/{name}"
LANGUAGES = {"dan": "da", "eng": "en", "ger": "de", "fre": "fr"}


def mend(raw: str) -> str:
    """Join the words the OCR split across a line: "Kre-\\naturer" is "Kreaturer"."""
    return re.sub(r"(\w)- *\n(\w)", r"\1\2", raw)


def ocr_file(item: str, files: list[dict]) -> str:
    """The item's OCR text. Uploads name it after the book, not the item, and
    some carry a near-empty `<item>_djvu.txt` beside the real one: take the largest."""
    ocr = [f for f in files if f.get("name", "").endswith("_djvu.txt")]
    return max(ocr, key=lambda f: int(f.get("size") or 0))["name"] if ocr else f"{item}_djvu.txt"


class Archive:
    name = "archive"
    source_name = "Internet Archive"
    source_type = "book"

    def fetch(self, query: str, limit: int):
        item, _, word = query.partition(" ")
        data = json.loads(download(META.format(id=item)))
        meta = data.get("metadata", {})
        title = meta.get("title") or item
        language = LANGUAGES.get(meta.get("language", ""), "da")
        name = quote(ocr_file(item, data.get("files", [])))
        text = mend(download(TEXT.format(id=item, name=name)).decode("utf-8", "replace"))
        for n, chunk in enumerate(windows(text, word.strip() or None)[:limit], 1):
            yield {
                "source_url": f"https://archive.org/details/{item}#{n}",
                "title": f"{title}, part {n}",
                "text": chunk,
                "language": language,
            }
