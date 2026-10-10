"""Wikimedia Commons pictures, found by a Commons search.

Query is a CirrusSearch string over files, e.g. 'deepcat:"Copenhagen in the
1970s"' or 'deepcat:"Demonstrations and protests in Copenhagen"'. One record a
picture: its caption, date, categories, licence and author as text, and its
point when Commons has one. `pipeline.pictures` looks at the picture itself
(docs/10, *A picture can be the memory*). Licences are checked there, against
`enrich.FREE`.
"""

import json
import re
import time
import urllib.parse

from crawler.gutenberg import download

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "memory-lane/1.0 (+https://github.com/linusaxel/memory-lane)"
PAUSE_S = 0.5
WIDTH = 1024
TAG = re.compile(r"<[^>]+>")


def _api(params: dict) -> dict:
    url = f"{API}?" + urllib.parse.urlencode(params | {"format": "json", "formatversion": 2})
    return json.loads(download(url, USER_AGENT))


def _meta(info: dict, key: str) -> str:
    value = str(info.get("extmetadata", {}).get(key, {}).get("value", ""))
    return " ".join(TAG.sub(" ", value).split())


def files(titles: list[str]) -> list[dict]:
    """Each file's picture, credit and point, in the order asked; images only."""
    out = []
    for i in range(0, len(titles), 50):
        pages = _api(
            {
                "action": "query",
                "titles": "|".join(titles[i : i + 50]),
                "prop": "imageinfo|coordinates",
                "iiprop": "url|extmetadata|mime",
                "iiurlwidth": WIDTH,
            }
        )["query"]["pages"]
        by_title = {p["title"]: p for p in pages}
        for t in titles[i : i + 50]:
            p = by_title.get(t, {})
            info = (p.get("imageinfo") or [{}])[0]
            if not info.get("mime", "").startswith("image/"):
                continue
            point = (p.get("coordinates") or [{}])[0]
            out.append(
                {
                    "title": t,
                    "url": info["url"],
                    "thumb": info.get("thumburl") or info["url"],
                    "page": info["descriptionurl"],
                    "caption": _meta(info, "ImageDescription") or t[5:],
                    "date": _meta(info, "DateTimeOriginal"),
                    "categories": _meta(info, "Categories"),
                    "author": _meta(info, "Artist")[:120],
                    "license": _meta(info, "LicenseShortName"),
                    "lat": point.get("lat"),
                    "lng": point.get("lon"),
                }
            )
    return out


def search(query: str, limit: int) -> list[str]:
    titles, offset = [], 0
    while len(titles) < limit:
        found = _api(
            {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srnamespace": 6,
                "srlimit": min(50, limit - len(titles)),
                "sroffset": offset,
            }
        )
        hits = [s["title"] for s in found["query"]["search"]]
        titles += hits
        if not hits or "continue" not in found:
            break
        offset = found["continue"]["sroffset"]
        time.sleep(PAUSE_S)
    return titles


def text_of(f: dict) -> str:
    where = f"\nCommons places this at {f['lat']}, {f['lng']}." if f["lat"] is not None else ""
    return (
        f"{f['title'][5:]} (Wikimedia Commons)\n\n{f['caption']}\n\nDate: {f['date']}\n"
        f"Categories: {f['categories']}\nAuthor: {f['author']}\nLicence: {f['license']}{where}"
    )


class Commons:
    name = "commons"
    source_name = "Wikimedia Commons"
    source_type = "picture"

    def fetch(self, query: str, limit: int):
        for f in files(search(query, limit)):
            yield {
                "source_url": f["page"],
                "title": f["title"][5:],
                "text": text_of(f),
                "lat": f["lat"],
                "lng": f["lng"],
            }
