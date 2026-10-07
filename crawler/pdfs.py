"""A local paper's or society's back issues, from the page that links their PDFs.

Query is "<index page url> [<from year>] [<via regex>]": every .pdf the page
links, newest first, optionally only from that year on (taken from the link).
With a via regex, the index links a page per issue (the links matching it), and
each of those pages links the PDF. Pauses as long as robots.txt's Crawl-delay. Text by
poppler's `pdftotext`, in windows of whole paragraphs. Typed press, so the text
is forgotten once extracted (pipeline.transcripts.forget).
"""

import itertools
import re
import subprocess
import time
import urllib.parse

from crawler.gutenberg import download, windows
from crawler.webpages import robots

USER_AGENT = "memory-lane/1.0 (+https://github.com/linusaxel/memory-lane)"
PAUSE_S = 1.0


def pdf_links(page: str, base: str, since: int | None = None, pattern=r"\.pdf$") -> list[str]:
    links = dict.fromkeys(
        urllib.parse.urljoin(base, h)
        for h in re.findall(r'href="([^"]+)"', page)
        if re.search(pattern, h, re.I)
    )
    year = lambda u: int(m[-1]) if (m := re.findall(r"(?<!\d)(?:19|20)\d\d(?!\d)", u)) else 0  # noqa: E731
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
        return itertools.islice(self._records(query), limit)

    def _records(self, query: str):
        url, *rest = query.split()
        since = next((int(t) for t in rest if t.isdigit()), None)
        via = next((t for t in rest if not t.isdigit()), None)
        pause = robots(url, USER_AGENT).crawl_delay(USER_AGENT) or PAUSE_S
        get = lambda u: download(u, USER_AGENT).decode("utf-8", "replace")  # noqa: E731
        index = get(url)
        pages = pdf_links(index, url, since, via) if via else [url]
        for page_url in pages:
            page = index if page_url == url else get(page_url)
            for link in pdf_links(page, page_url, None if via else since):
                time.sleep(pause)
                title = urllib.parse.unquote(link.rsplit("/", 1)[-1])
                for i, window in enumerate(windows(pdf_text(download(link, USER_AGENT)))):
                    yield {
                        "source_url": f"{link}#{i}",
                        "title": title,
                        "text": window,
                        "language": "da",
                    }
