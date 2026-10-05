"""A local paper's or society's back issues, from the page that links their PDFs.

Query is "<index page url> [<from year>]": every .pdf the page links, newest
first, optionally only from that year on (taken from the link). Text by
poppler's `pdftotext`, in windows of whole paragraphs. Typed press, so the text
is forgotten once extracted (pipeline.transcripts.forget).
"""

import re
import subprocess
import time
import urllib.parse

from crawler.gutenberg import download, windows

USER_AGENT = "memory-lane/1.0 (+https://github.com/linusaxel/memory-lane)"
PAUSE_S = 1.0


def pdf_links(page: str, base: str, since: int | None = None) -> list[str]:
    links = dict.fromkeys(
        urllib.parse.urljoin(base, h) for h in re.findall(r'href="([^"]+\.pdf)"', page, re.I)
    )
    year = lambda u: int(m[0]) if (m := re.findall(r"(?<!\d)(?:19|20)\d\d(?!\d)", u)) else 0  # noqa: E731
    return sorted((u for u in links if since is None or year(u) >= since), key=year, reverse=True)


def pdf_text(data: bytes) -> str:
    return subprocess.run(
        ["pdftotext", "-q", "-", "-"], input=data, capture_output=True, check=True
    ).stdout.decode("utf-8", "replace")


class Pdfs:
    name = "pdfs"
    source_name = "PDF archive"  # the credit is the sources row's name
    source_type = "press"

    def fetch(self, query: str, limit: int):
        url, _, since = query.partition(" ")
        page = download(url, USER_AGENT).decode("utf-8", "replace")
        n = 0
        for link in pdf_links(page, url, int(since) if since else None):
            time.sleep(PAUSE_S)
            title = urllib.parse.unquote(link.rsplit("/", 1)[-1])
            for i, window in enumerate(windows(pdf_text(download(link, USER_AGENT)))):
                if n >= limit:
                    return
                n += 1
                yield {
                    "source_url": f"{link}#{i}",
                    "title": title,
                    "text": window,
                    "language": "da",
                }
