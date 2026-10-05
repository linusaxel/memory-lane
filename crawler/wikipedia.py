"""Wikipedia articles about places, found by where they stand.

Query is "<lang> <lat>,<lng> <metres>", e.g. "da 55.6761,12.5683 2000": the
articles Wikipedia geotags within that radius (at most 10 km), nearest first.
Or "<lang> category:<name>|<name>", e.g. "en category:Crime in Copenhagen|Cinemas
in Copenhagen": the categories' geotagged articles, longest first, which skips
the stubs and the citywide article a radius drags in. Either way as plain
text without their reference sections, in windows of whole paragraphs. Most of an
article is description the extractor's judge rejects; the incidents in its
history are what it keeps. CC BY-SA: our own words, credited by the link
(docs/10, *The sources' legal footing*).
"""

import json
import re
import time
import urllib.parse

from crawler.gutenberg import download, windows

USER_AGENT = "memory-lane/1.0 (+https://github.com/linusaxel/memory-lane)"
PAUSE_S = 0.5
# Sections that are lists of sources and links, never a story.
NOT_A_STORY = re.compile(
    r"^(references|notes|sources|see also|external links|further reading|bibliography|"
    r"gallery|litteratur|kilder|noter|referencer|se også|eksterne henvisninger|"
    r"galleri|henvisninger)$",
    re.I,
)


def _api(lang: str, params: dict) -> dict:
    url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        params | {"format": "json", "formatversion": 2}
    )
    return json.loads(download(url, USER_AGENT))


def article_text(lang: str, title: str) -> str:
    """The article as plain text, without the sections that only cite."""
    pages = _api(
        lang,
        {
            "action": "query",
            "prop": "extracts",
            "explaintext": 1,
            "exsectionformat": "wiki",
            "titles": title,
        },
    )["query"]["pages"]
    raw = pages[0].get("extract", "") if pages else ""
    kept, section, skip = [], False, False
    for line in raw.splitlines():
        heading = re.fullmatch(r"(=+)\s*(.*?)\s*\1", line.strip())
        if heading:
            # A subsection of a skipped section is skipped with it.
            if heading[1] == "==":
                section = bool(NOT_A_STORY.match(heading[2]))
            skip = section or bool(NOT_A_STORY.match(heading[2]))
            if not skip:
                kept.append(f"\n{heading[2]}\n")
            continue
        if not skip:
            kept.append(line)
    return "\n".join(kept).strip()


def categories(lang: str, names: str) -> list[dict]:
    """The geotagged articles of "A|B", each once, longest first.
    ponytail: one page of 500 members a category; follow `continue` past that."""
    pages = {}
    for name in names.split("|"):
        for p in (
            _api(
                lang,
                {
                    "action": "query",
                    "generator": "categorymembers",
                    "gcmtitle": f"Category:{name.strip()}",
                    "gcmnamespace": 0,
                    "gcmlimit": 500,
                    "prop": "info|coordinates",
                    "colimit": "max",
                },
            )
            .get("query", {})
            .get("pages", [])
        ):
            if p.get("coordinates"):
                pages[p["title"]] = p
    return [
        {"title": p["title"], "lat": p["coordinates"][0]["lat"], "lon": p["coordinates"][0]["lon"]}
        for p in sorted(pages.values(), key=lambda p: -p.get("length", 0))
    ]


def parse_query(query: str) -> tuple[str, float, float, int]:
    lang, point, metres = query.split()
    lat, lng = (float(x) for x in point.split(","))
    return lang, lat, lng, min(int(metres), 10_000)


class Wikipedia:
    name = "wikipedia"
    source_name = "Wikipedia"
    source_type = "encyclopedia"

    def fetch(self, query: str, limit: int):
        lang, _, rest = query.partition(" ")
        if rest.startswith("category:"):
            yield from self._windows(lang, categories(lang, rest.removeprefix("category:")), limit)
            return
        lang, lat, lng, metres = parse_query(query)
        found = _api(
            lang,
            {
                "action": "query",
                "list": "geosearch",
                "gscoord": f"{lat}|{lng}",
                "gsradius": metres,
                "gslimit": 500,
            },
        )["query"]["geosearch"]
        yield from self._windows(lang, found, limit)

    def _windows(self, lang: str, found: list[dict], limit: int):
        n = 0
        for page in found:
            time.sleep(PAUSE_S)
            url = f"https://{lang}.wikipedia.org/wiki/" + urllib.parse.quote(
                page["title"].replace(" ", "_")
            )
            body = article_text(lang, page["title"])
            for i, window in enumerate(windows(body)):
                if n >= limit:
                    return
                n += 1
                yield {
                    "source_url": f"{url}#{i}",
                    "title": page["title"],
                    "text": f"{page['title']} (Wikipedia)\n\n{window}\n\n"
                    f"Wikipedia places this at {page['lat']}, {page['lon']}.",
                    "language": lang,
                    "lat": page["lat"],
                    "lng": page["lon"],
                }
