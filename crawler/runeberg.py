"""Nordic public-domain books from Projekt Runeberg, proofread from the scans.

The query is the work key, optionally followed by a word, as for Gutenberg:
"studdagene" or "gmlivs/1 Østergade". A volume of a multi-volume work is
`<key>/<n>`. Every work downloads as a zip with one text file per printed page.
"""

import io
import re
import zipfile

from crawler.gutenberg import download, windows

URL = "https://runeberg.org/download.pl?mode=txtzip&work={work}"
USER_AGENT = "memory-lane/1.0 (+https://github.com/linusaxel/memory-lane)"


def book(data: bytes) -> tuple[str | None, str | None, str]:
    """Title, language and the pages joined in order, from a Runeberg zip.
    A page opens with its printed page number, which is dropped."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        raw = z.read("Metadata")
        try:
            meta = raw.decode("utf-8")
        except UnicodeDecodeError:  # older works write it in Latin-1
            meta = raw.decode("latin-1")
        pages = sorted(n for n in z.namelist() if re.fullmatch(r"Pages/\d+\.txt", n))
        text = "\n\n".join(
            re.sub(r"\A\s*\d+\s*\n", "", z.read(n).decode("utf-8", "replace")) for n in pages
        )

    def field(name):
        m = re.search(rf"^{name}: *(.+)$", meta, re.MULTILINE)
        return m.group(1).strip() if m else None

    return field("TITLE"), field("LANGUAGE"), text


class Runeberg:
    name = "runeberg"
    source_name = "Projekt Runeberg"
    source_type = "book"

    def fetch(self, query: str, limit: int):
        work, _, word = query.partition(" ")
        title, language, text = book(download(URL.format(work=work), USER_AGENT))
        title = title or work
        for n, chunk in enumerate(windows(text, word.strip() or None)[:limit], 1):
            yield {
                "source_url": f"https://runeberg.org/{work}/#{n}",
                "title": f"{title}, part {n}",
                "text": chunk,
                "language": language or "da",
            }
