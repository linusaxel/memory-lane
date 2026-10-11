"""A site's own pages: one page, or every page a sitemap lists.

Query is "<page url>" or "<sitemap .xml url> [<url regex>]": the paragraphs of
each page, in windows. Skips what robots.txt disallows and pauses as long as its
Crawl-delay. Typed press, so the text is forgotten once extracted
(pipeline.transcripts.forget).
"""

import html
import itertools
import re
import time
import urllib.error
import urllib.parse
import urllib.robotparser

from crawler.gutenberg import download, windows
from crawler.rss import paragraphs

USER_AGENT = "memory-lane/1.0 (+https://github.com/linusaxel/memory-lane)"
PAUSE_S = 1.0


def sitemap_urls(xml: str, pattern: str | None = None) -> list[str]:
    urls = dict.fromkeys(html.unescape(u) for u in re.findall(r"<loc>([^<]+)</loc>", xml))
    return [u for u in urls if pattern is None or re.search(pattern, u)]


def decoded(body: bytes) -> str:
    """UTF-8, else what an old Danish homepage is: UTF-16 by its BOM, or Windows-1252."""
    if body.startswith((b"\xff\xfe", b"\xfe\xff")):
        return body.decode("utf-16")
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError:
        return body.decode("cp1252", "replace")


def page_text(raw: str) -> str:
    """A page's paragraphs; an old homepage writes with <br> and <font>, not
    <p>, so when they hold under a quarter of its text, all of its text."""
    body, every = paragraphs(raw), paragraphs(raw, every=True)
    return body if len(body) * 4 >= len(every) else every


def robots(url: str, user_agent: str = USER_AGENT) -> urllib.robotparser.RobotFileParser:
    """The site's robots.txt, fetched as us: RobotFileParser.read() fetches as
    Python-urllib, which some sites answer with 403, and it then disallows all."""
    parser = urllib.robotparser.RobotFileParser()
    try:
        lines = download(urllib.parse.urljoin(url, "/robots.txt"), user_agent, tries=1)
        parser.parse(lines.decode("utf-8", "replace").splitlines())
    except urllib.error.HTTPError as e:
        parser.disallow_all = e.code in (401, 403)
        parser.parse([])
    return parser


class Webpages:
    name = "webpages"
    source_name = "Web pages"  # the credit is the sources row's name
    source_type = "press"

    def fetch(self, query: str, limit: int):
        return itertools.islice(self._records(query), limit)

    def _records(self, query: str):
        url, _, pattern = query.partition(" ")
        rules = robots(url)
        pause = rules.crawl_delay(USER_AGENT) or PAUSE_S
        get = lambda u: decoded(download(u, USER_AGENT))  # noqa: E731
        xml = urllib.parse.urlparse(url).path.endswith(".xml")
        pages = sitemap_urls(get(url), pattern or None) if xml else [url]
        for page in pages:
            if not rules.can_fetch(USER_AGENT, page):
                continue
            time.sleep(pause)
            raw = get(page)
            title = m[1].strip() if (m := re.search(r"<title>([^<]*)", raw)) else page
            for i, window in enumerate(windows(page_text(raw))):
                yield {
                    "source_url": f"{page}#{i}",
                    "title": html.unescape(title),
                    "text": window,
                }
