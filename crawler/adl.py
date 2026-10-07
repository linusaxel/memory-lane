"""Johanne Luise Heiberg's memoirs from Arkiv for Dansk Litteratur (tekster.kb.dk).

The query is the volume id, optionally followed by a word, as for Runeberg:
"heibfr05val Kongens Nytorv". Only the 1944 edition's three volumes are FRI on
KB's copyright list; every other ADL text, Heiberg's 1973 volumes among them,
is refused (docs/10, *The sources' legal footing*).
"""

from html.parser import HTMLParser

from crawler.gutenberg import download, windows

URL = "https://tekster.kb.dk/text/adl-texts-{id}-root"
FREE = {"heibfr05val", "heibfr06val", "heibfr07val"}
VOID = {"br", "img", "hr", "wbr"}
SKIP = {"symbol quote", "note", "note_content", "pageBreak"}


class _Paragraphs(HTMLParser):
    """The text of each <p class="paragraph">, without the page's scissor
    links, page numbers and editor's notes."""

    def __init__(self):
        super().__init__()
        self.paragraphs: list[str] = []
        self.title: str | None = None
        self._in_title = False
        self._open: list[str] = []  # tags inside the current paragraph
        self._skipping = 0  # depth inside a skipped element, 0 for none

    def handle_starttag(self, tag, attrs):
        cls = dict(attrs).get("class") or ""
        if tag == "title":
            self._in_title = True
        if tag == "p" and cls == "paragraph" and not self._open:
            self._open = ["p"]
            self.paragraphs.append("")
            return
        if not self._open or tag in VOID:
            return
        self._open.append(tag)
        if self._skipping or cls in SKIP or tag == "script":
            self._skipping += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if not self._open or tag in VOID:
            return
        self._open.pop()
        if self._skipping:
            self._skipping -= 1

    def handle_data(self, data):
        if self._in_title and self.title is None:
            self.title = data.split(" - ")[0].strip()
        if self._open and not self._skipping:
            self.paragraphs[-1] += data


def book(page: str) -> tuple[str | None, str]:
    """Title and the paragraphs, one to a blank-line-separated block."""
    parser = _Paragraphs()
    parser.feed(page)
    text = "\n\n".join(" ".join(p.split()) for p in parser.paragraphs)
    return parser.title, text


class Adl:
    name = "adl"
    source_name = "Arkiv for Dansk Litteratur"
    source_type = "book"

    def fetch(self, query: str, limit: int):
        volume, _, word = query.partition(" ")
        if volume not in FREE:
            raise ValueError(f"{volume} is not one of the FRI volumes {sorted(FREE)}")
        title, text = book(download(URL.format(id=volume)).decode("utf-8"))
        title = f"Et Liv gjenoplevet i Erindringen, {title or volume}"
        for n, chunk in enumerate(windows(text, word.strip() or None)[:limit], 1):
            yield {
                "source_url": f"{URL.format(id=volume)}#{n}",
                "title": f"{title}, part {n}",
                "text": chunk,
                "language": "da",
            }
