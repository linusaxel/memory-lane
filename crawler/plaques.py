"""Plaques and inscribed memorials from OpenStreetMap, with the Wikipedia intro
of who or what they commemorate.

A plaque is a story that already names its spot: "In this building eleven
people died in the bombing of the Shellhus, 21 March 1945." Query is a box,
south,west,north,east. OSM is ODbL (credit "© OpenStreetMap contributors");
Wikipedia is CC BY-SA, credited by its link (docs/10, *The sources' legal
footing*).
"""

import json
import time
import urllib.parse

from crawler.gutenberg import download

OVERPASS = "https://overpass-api.de/api/interpreter"
WIKIDATA = "https://www.wikidata.org/w/api.php"
USER_AGENT = "memory-lane/1.0 (+https://github.com/linusaxel/memory-lane)"
WIKIS = ("dawiki", "enwiki")
PAUSE_S = 1.0


def _json(url: str, data: dict | None = None) -> dict:
    if data:
        url = f"{url}?{urllib.parse.urlencode(data)}"
    return json.loads(download(url, USER_AGENT))


def query_for(box: str) -> str:
    s, w, n, e = (float(x) for x in box.split(","))
    b = f"({s},{w},{n},{e})"
    return (
        "[out:json][timeout:90];("
        f'nwr["memorial"="plaque"]{b};'
        f'nwr["memorial:type"="plaque"]{b};'
        f'nwr["historic"="memorial"]["inscription"]{b};'
        ");out center tags;"
    )


def intro(tags: dict) -> tuple[str, str] | None:
    """(article URL, its intro) for what the plaque commemorates, or None."""
    title = tags.get("subject:wikipedia") or tags.get("wikipedia")
    if not title and (qid := tags.get("subject:wikidata") or tags.get("wikidata")):
        found = _json(
            WIKIDATA,
            {
                "action": "wbgetentities",
                "ids": qid.split(";")[0],
                "props": "sitelinks",
                "sitefilter": "|".join(WIKIS),
                "format": "json",
            },
        )
        links = next(iter(found.get("entities", {}).values()), {}).get("sitelinks", {})
        wiki = next((w for w in WIKIS if w in links), None)
        title = wiki and f"{wiki[:2]}:{links[wiki]['title']}"
    if not title or ":" not in title:
        return None
    lang, name = title.split(":", 1)
    page = urllib.parse.quote(name.replace(" ", "_"))
    summary = _json(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{page}")
    url = summary.get("content_urls", {}).get("desktop", {}).get("page")
    return (url, summary.get("extract", "")) if url and summary.get("extract") else None


def record(element: dict, about: tuple[str, str] | None) -> dict | None:
    tags = element.get("tags", {})
    inscription = " ".join(tags.get("inscription", "").replace(" / ", " ").split())
    name = tags.get("name") or tags.get("subject") or ""
    if not inscription and not about:
        return None
    lat = element.get("lat") or element.get("center", {}).get("lat")
    lng = element.get("lon") or element.get("center", {}).get("lon")
    address = " ".join(filter(None, (tags.get("addr:street"), tags.get("addr:housenumber"))))
    lines = [
        f"A plaque{f' at {address}' if address else ''}: {name}".rstrip(": "),
        f"Inscription: {inscription}" if inscription else "",
        f"Unveiled: {tags['start_date']}" if tags.get("start_date") else "",
        f"About its subject, from Wikipedia ({about[0]}): {about[1]}" if about else "",
        f"OpenStreetMap places this plaque at {lat}, {lng}.",
    ]
    return {
        "source_url": f"https://www.openstreetmap.org/{element['type']}/{element['id']}",
        "title": name or inscription[:80],
        "text": "\n\n".join(x for x in lines if x),
        "language": "da",
        "lat": lat,
        "lng": lng,
    }


class Plaques:
    name = "plaques"
    source_name = "OpenStreetMap plaques"
    source_type = "plaque"

    def fetch(self, query: str, limit: int):
        found = json.loads(
            download(f"{OVERPASS}?{urllib.parse.urlencode({'data': query_for(query)})}", USER_AGENT)
        )
        n = 0
        for element in found.get("elements", []):
            if n >= limit:
                return
            time.sleep(PAUSE_S)
            try:
                about = intro(element.get("tags", {}))
            except (
                OSError,
                ValueError,
            ):
                about = None
            if r := record(element, about):
                n += 1
                yield r
