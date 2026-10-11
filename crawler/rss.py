"""Recent stories from a feed: a paper's articles, or a podcast's transcripts.

Query is the feed's URL. Press takes each item's full text from the feed when
it carries it (content:encoded), else the paragraphs of the article's page. A
podcast takes the Podcasting 2.0 <podcast:transcript> an item links to, and
skips an episode without one: no audio is transcribed here. Neither text is
kept once extracted, as a video's captions aren't (pipeline.transcripts.forget):
we write facts in our own words and link back (docs/10, *The sources' legal
footing*). Which feeds are fit to use is the find-sources skill's question.
"""

import json
import re
import time
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

from crawler.gutenberg import download, windows

USER_AGENT = "memory-lane/1.0 (+https://github.com/linusaxel/memory-lane)"
PAUSE_S = 1.0
NS = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "podcast": "https://podcastindex.org/namespace/1.0",
}
# Plain text first: it needs no cleaning. HTML last: it needs the most.
TRANSCRIPT_TYPES = ("text/plain", "text/vtt", "application/x-subrip", "application/srt")
TRANSCRIPT_TYPES += ("application/json", "text/html")


class _Paragraphs(HTMLParser):
    """The text inside <p>, one paragraph each: an article's body, not its menus.
    With `every`, the text outside <p> too; never a script's or a style's."""

    def __init__(self, every: bool = False):
        super().__init__()
        self.paragraphs, self._open, self._every, self._code = [], 0, every, 0

    def handle_starttag(self, tag, attrs):
        if tag == "p":
            self._open += 1
            self.paragraphs.append("")
        elif tag in ("script", "style"):
            self._code += 1

    def handle_endtag(self, tag):
        if tag == "p" and self._open:
            self._open -= 1
        elif tag in ("script", "style") and self._code:
            self._code -= 1

    def handle_data(self, data):
        if self._code:
            return
        if self._open:
            self.paragraphs[-1] += data
        elif self._every and data.strip():
            self.paragraphs.append(data)


def paragraphs(html: str, every: bool = False) -> str:
    parser = _Paragraphs(every)
    parser.feed(html)
    return "\n\n".join(" ".join(p.split()) for p in parser.paragraphs if p.strip())


def transcript_text(raw: str, kind: str) -> str:
    """A transcript file as plain text: cue numbers and timings gone."""
    if kind == "application/json":
        return " ".join(s.get("body", "") for s in json.loads(raw).get("segments", []))
    if kind == "text/html":
        return paragraphs(raw, every=True)
    lines = [
        line.strip()
        for line in raw.splitlines()
        if line.strip()
        and "-->" not in line
        and not line.strip().isdigit()
        and not line.startswith(("WEBVTT", "NOTE"))
    ]
    return re.sub(r"<[^>]+>", "", " ".join(lines))


def items(feed: bytes) -> list[ET.Element]:
    return ET.fromstring(feed).findall("./channel/item")


def _text(item: ET.Element, path: str) -> str:
    return (item.findtext(path, default="", namespaces=NS) or "").strip()


def _transcript(item: ET.Element) -> ET.Element | None:
    found = {t.get("type"): t for t in item.findall("podcast:transcript", NS)}
    return next((found[k] for k in TRANSCRIPT_TYPES if k in found), None)


def _records(url: str, title: str, body: str, language: str):
    for i, window in enumerate(windows(body)):
        yield {
            "source_url": f"{url}#{i}" if i else url,
            "title": title,
            "text": f"{title}\n\n{window}",
            "language": language,
        }


class Press:
    name = "press"
    source_name = "Press"
    source_type = "press"

    def fetch(self, query: str, limit: int):
        feed = download(query, USER_AGENT)
        language = (ET.fromstring(feed).findtext("./channel/language") or "da")[:2]
        for item in items(feed)[:limit]:
            link, title = _text(item, "link"), _text(item, "title")
            body = paragraphs(_text(item, "content:encoded"))
            if not body and link:
                time.sleep(PAUSE_S)
                body = paragraphs(download(link, USER_AGENT).decode("utf-8", "replace"))
            if link and body:
                yield from _records(link, title, body, language)


class Podcast:
    name = "podcast"
    source_name = "Podcast"
    source_type = "podcast"

    def fetch(self, query: str, limit: int):
        feed = download(query, USER_AGENT)
        language = (ET.fromstring(feed).findtext("./channel/language") or "da")[:2]
        for item in items(feed)[:limit]:
            tag = _transcript(item)
            if tag is None:
                continue
            time.sleep(PAUSE_S)
            raw = download(tag.get("url"), USER_AGENT).decode("utf-8", "replace")
            link = _text(item, "link") or tag.get("url")
            yield from _records(
                link, _text(item, "title"), transcript_text(raw, tag.get("type")), language
            )
