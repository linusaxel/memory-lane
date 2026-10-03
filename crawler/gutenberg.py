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

URL = "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt"
# ponytail: a guess, about 2k tokens; one window is one extraction chunk.
WINDOW_CHARS = 8000
LANGUAGES = {"English": "en", "Danish": "da", "German": "de", "French": "fr"}


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


def windows(raw: str, word: str | None = None) -> list[str]:
    """The book between Gutenberg's START and END lines, in paragraph-aligned
    windows; with `word`, only the windows that mention it."""
    start = re.search(r"^\*\*\* ?START OF.*$", raw, re.MULTILINE)
    end = re.search(r"^\*\*\* ?END OF.*$", raw, re.MULTILINE)
    body = raw[start.end() if start else 0 : end.start() if end else len(raw)]
    out, current = [], ""
    for para in re.split(r"\n\s*\n", body):
        para = " ".join(para.split())
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
