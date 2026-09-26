"""Historisk Atlas stories, found by title in the sitemap.

Pages are server-rendered with the story as JSON in `window.passed.geo`, and
robots.txt disallows nothing. Only title and intro are public: `contents` is
null until the API access asked for in TODO.md arrives. Query "Sabotage" for
the WWII resistance set (geoid 19000-20000): exact dates, exact places.
"""

import html
import json
import re
import time
import urllib.parse
import urllib.request

SITEMAP = "https://historiskatlas.dk/sitemap.xml"
USER_AGENT = "memory-lane/1.0 (+https://github.com/linusaxel/memory-lane)"
PAUSE_S = 1.0


def _get(url: str) -> str:
    # Unencoded æøå fail about half the time.
    url = urllib.parse.quote(url, safe=":/()_,.-%")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as r:
        return r.read().decode("utf-8-sig")


def _geo(page: str) -> dict | None:
    start = page.find("geo: {")
    if start < 0:
        return None
    return json.JSONDecoder().raw_decode(page, start + len("geo: "))[0]


class HistoriskAtlas:
    name = "historisk-atlas"
    source_name = "Historisk Atlas"
    source_type = "archive"

    def fetch(self, query: str, limit: int):
        urls = [html.unescape(u) for u in re.findall(r"<loc>([^<]+)</loc>", _get(SITEMAP))]
        urls = [u for u in urls if query.lower() in urllib.parse.unquote(u).lower()]
        for url in urls[:limit]:
            time.sleep(PAUSE_S)
            geo = _geo(_get(url))
            if not geo or not (geo.get("intro") or "").strip():
                continue
            # ponytail: the atlas's own point reaches the pin only through the
            # model's lat/lng, which a geocoder hit can still override; a
            # coordinate on `content` if pins land off the atlas's.
            yield {
                "source_url": urllib.parse.quote(url, safe=":/()_,.-%"),
                "title": geo["title"],
                "text": f"{geo['title']}\n\n{geo['intro'].strip()}\n\n"
                f"Historisk Atlas places this at {geo['latitude']}, {geo['longitude']}.",
                "language": "da",
            }
