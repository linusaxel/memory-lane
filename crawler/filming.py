"""Films and series shot at a spot, from Wikidata's filming locations (P915),
with what the film's Wikipedia article says about the shoot.

Query is a box, south,west,north,east. A location with a population is a
city or a district, not a spot ("filmed in Copenhagen"), so it is left out;
studios stay, since "Matador was shot here" is a walk. Wikidata is CC0,
Wikipedia CC BY-SA, credited by the link.
"""

import json
import re
import time
import urllib.parse

from crawler.gutenberg import download
from crawler.wikipedia import article_text

SPARQL = "https://query.wikidata.org/sparql"
USER_AGENT = "memory-lane/1.0 (+https://github.com/linusaxel/memory-lane)"
PAUSE_S = 1.0
# The article's paragraphs about the shoot, in the languages we read it in.
SHOOT = re.compile(r"optag|filmet|filmed|filming|shot |location|scene|indspil", re.I)

QUERY = """
SELECT ?film ?filmLabel ?loc ?locLabel ?lat ?lng (SAMPLE(?da) AS ?daw) (SAMPLE(?en) AS ?enw)
WHERE {
  ?film wdt:P915 ?loc .
  SERVICE wikibase:box {
    ?loc wdt:P625 ?coord .
    bd:serviceParam wikibase:cornerSouthWest "Point(%(w)s %(s)s)"^^geo:wktLiteral .
    bd:serviceParam wikibase:cornerNorthEast "Point(%(e)s %(n)s)"^^geo:wktLiteral .
  }
  FILTER NOT EXISTS { ?loc wdt:P1082 [] }
  BIND(geof:latitude(?coord) AS ?lat) BIND(geof:longitude(?coord) AS ?lng)
  OPTIONAL { ?da schema:about ?film ; schema:isPartOf <https://da.wikipedia.org/> }
  OPTIONAL { ?en schema:about ?film ; schema:isPartOf <https://en.wikipedia.org/> }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "da,en". }
} GROUP BY ?film ?filmLabel ?loc ?locLabel ?lat ?lng
"""


def shoot(body: str, place: str) -> str:
    """The paragraphs about the shoot or the place, else the article's opening."""
    paragraphs = [p for p in body.split("\n") if p.strip()]
    about = [p for p in paragraphs if place.lower() in p.lower() or SHOOT.search(p)]
    return "\n\n".join((about or paragraphs[:3])[:12])


def record(row: dict, body: str) -> dict:
    film, place = row["filmLabel"]["value"], row["locLabel"]["value"]
    article = (row.get("daw") or row.get("enw") or {}).get("value")
    lat, lng = float(row["lat"]["value"]), float(row["lng"]["value"])
    text = (
        f"{film} was filmed at {place}, according to Wikidata.\n\n"
        + (
            f"From the Wikipedia article on {film} ({article}):\n\n{shoot(body, place)}\n\n"
            if body
            else ""
        )
        + f"Wikidata places {place} at {lat}, {lng}."
    )
    return {
        "source_url": f"{row['film']['value']}#{row['loc']['value'].rsplit('/', 1)[-1]}",
        "title": f"{film} at {place}",
        "text": text,
        "language": "da" if row.get("daw") else "en",
        "lat": lat,
        "lng": lng,
    }


class Filming:
    name = "filming"
    source_name = "Wikidata filming locations"
    source_type = "film"

    def fetch(self, query: str, limit: int):
        s, w, n, e = (float(x) for x in query.split(","))
        url = f"{SPARQL}?" + urllib.parse.urlencode(
            {"query": QUERY % {"s": s, "w": w, "n": n, "e": e}, "format": "json"}
        )
        rows = json.loads(download(url, USER_AGENT))["results"]["bindings"]
        for row in rows[:limit]:
            article = (row.get("daw") or row.get("enw") or {}).get("value")
            body = ""
            if article:
                time.sleep(PAUSE_S)
                lang = urllib.parse.urlparse(article).netloc.split(".")[0]
                title = urllib.parse.unquote(article.rsplit("/wiki/", 1)[-1]).replace("_", " ")
                body = article_text(lang, title)
            yield record(row, body)
