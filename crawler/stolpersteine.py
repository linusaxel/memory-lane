"""Stolpersteine, from German Wikipedia's per-city lists.

The query is the list's title, e.g. "Liste der Stolpersteine im Großraum
Kopenhagen". Every city's list is the same table: the stone, its inscription,
the address, the person's life. One record per address, so a family laid at one
door is one story. The rows carry no coordinates; the model names the address
and the geocoder places it. CC BY-SA, retold in our own words (docs/10, *The
sources' legal footing*).
"""

import json
import re
import urllib.parse

from crawler.gutenberg import download
from crawler.wikipedia import USER_AGENT


def _plain(wikitext: str) -> str:
    t = re.sub(r"<!--.*?-->|<ref[^>/]*/>|<ref[^>]*>.*?</ref>", "", wikitext, flags=re.S)
    t = re.sub(r"\{\{PersonZelle\|([^|}]*)\|([^|}]*)[^}]*\}\}", r"\1 \2", t)
    t = re.sub(r"\{\{[^{}]*\}\}", "", t)
    t = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"<br\s*/?>", "\n", t)
    t = re.sub(r"<[^>]+>|'''?", "", t)
    return re.sub(r"[ \t]+", " ", t).strip()


def stones(wikitext: str) -> dict[str, list[tuple[str, str]]]:
    """{address: [(inscription, life), ...]}, in the list's order."""
    by_address: dict[str, list[tuple[str, str]]] = {}
    full: dict[str, str] = {}  # street line -> the whole address, as first written
    for row in wikitext.split("\n|-")[1:]:
        cells = re.split(r"\n\|", row.split("\n|}")[0])[1:]
        if len(cells) < 4:
            continue
        inscription = _plain(cells[1].split("|", 1)[-1])
        lines = _plain(cells[2]).split("\n")
        # Keyed on the street line: the district under it is spelled out on some rows, not others.
        address = full.setdefault(" ".join(lines[0].split()), " ".join(" ".join(lines).split()))
        by_address.setdefault(address, []).append((inscription, _plain(cells[3])))
    return by_address


class Stolpersteine:
    name = "stolpersteine"
    source_name = "Wikipedia, Stolpersteine"
    source_type = "encyclopedia"

    def fetch(self, query: str, limit: int):
        params = {"action": "parse", "page": query, "prop": "wikitext", "format": "json"}
        url = "https://de.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
            params | {"formatversion": 2}
        )
        wikitext = json.loads(download(url, USER_AGENT))["parse"]["wikitext"]
        page = "https://de.wikipedia.org/wiki/" + urllib.parse.quote(query.replace(" ", "_"))
        for i, (address, people) in enumerate(stones(wikitext).items()):
            if i >= limit:
                return
            lives = "\n\n".join(f"Stone: {ins}\n\n{life}" for ins, life in people)
            yield {
                "source_url": f"{page}#{urllib.parse.quote(address)}",
                "title": f"Stolpersteine, {address}",
                "text": f"Stolpersteine at {address}\n\n{lives}",
                "language": "de",
            }
