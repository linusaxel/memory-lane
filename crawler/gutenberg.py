"""Public-domain books from Project Gutenberg, one plain-text file per book.

The query is the ebook number, optionally followed by a word: "3529 Copenhagen"
keeps only the stretches of Wollstonecraft's letters that name Copenhagen, so
Sweden and Norway are not billed. Headings differ in every book, so the text is
packed into windows of whole paragraphs instead of split on chapters.
"""

import http.client
import re
import time
import urllib.request
from collections import Counter

URL = "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt"
# ponytail: a guess, about 2k tokens; one window is one extraction chunk.
WINDOW_CHARS = 8000
LANGUAGES = {"English": "en", "Danish": "da", "German": "de", "French": "fr"}
# A page number, its 1s sometimes read as I, i or l: "34", "— i6 —", "^^8".
PAGE_NUMBER = re.compile(r"\W*[\dIil]*\d[\dIil]*\W*")


def download(url: str, user_agent: str | None = None, tries: int = 3) -> bytes:
    """The whole body, retried: both sites drop connections and cut bodies short."""
    headers = {"User-Agent": user_agent} if user_agent else {}
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=headers), timeout=120
            ) as r:
                return r.read()
        except (OSError, http.client.HTTPException):
            if attempt == tries - 1:
                raise
            time.sleep(5 * (attempt + 1))
    raise AssertionError("unreachable")


def _header(raw: str, field: str) -> str | None:
    m = re.search(rf"^{field}: *(.+)$", raw, re.MULTILINE)
    return m.group(1).strip() if m else None


def _letters(para: str) -> str:
    return re.sub(r"[\W\d_]", "", para).lower()


def unpaged(paras: list[str]) -> list[str]:
    """The paragraphs without what a scan prints on every page: a bare page
    number, and a short running head ("Otto Zinck: Erindringer 3") seen five
    times or more. Both split a place name mid-phrase."""
    seen = Counter(_letters(p) for p in paras if len(p) <= 60)
    return [
        p
        for p in paras
        if not PAGE_NUMBER.fullmatch(p)
        and not (len(p) <= 60 and len(_letters(p)) >= 8 and seen[_letters(p)] >= 5)
    ]


def windows(raw: str, word: str | None = None) -> list[str]:
    """The book between Gutenberg's START and END lines, in paragraph-aligned
    windows; with `word`, only the windows that mention it."""
    start = re.search(r"^\*\*\* ?START OF.*$", raw, re.MULTILINE)
    end = re.search(r"^\*\*\* ?END OF.*$", raw, re.MULTILINE)
    body = raw[start.end() if start else 0 : end.start() if end else len(raw)]
    out, current = [], ""
    for para in unpaged([" ".join(p.split()) for p in re.split(r"\n\s*\n", body)]):
        if not para:
            continue
        if current and len(current) + len(para) > WINDOW_CHARS:
            out.append(current)
            current = ""
        current = f"{current}\n\n{para}" if current else para
    if current:
        out.append(current)
    return [w for w in out if not word or word.lower() in w.lower()]


class Gutenberg:
    name = "gutenberg"
    source_name = "Project Gutenberg"
    source_type = "book"

    def fetch(self, query: str, limit: int):
        book_id, _, word = query.partition(" ")
        raw = download(URL.format(id=int(book_id))).decode("utf-8-sig")
        title = _header(raw, "Title") or f"Gutenberg #{book_id}"
        language = LANGUAGES.get(_header(raw, "Language") or "", "en")
        for n, text in enumerate(windows(raw, word.strip() or None)[:limit], 1):
            yield {
                "source_url": f"https://www.gutenberg.org/ebooks/{book_id}#{n}",
                "title": f"{title}, part {n}",
                "text": text,
                "language": language,
            }
