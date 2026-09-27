"""The model names a place; free geocoders place it. See
docs/10-decisions.md#the-llm-names-the-place-free-geocoders-place-it.

Every geocoder here answers something for almost any query, so one guard,
`place()`, judges all of them. The traps it exists for, found live 2026-09-26:
- Photon: "Blaagaardsgade 12" -> Moltkes Palæ, another building. The name must match.
- Photon: CBGB (closed 2006) -> the centre of New York. A city is not a place.
- DAWA: "Nonexistentgade 999" -> Vestergade 9, Nibe. The street must match.
- Copenhagen renumbered its houses in 1859: an old number is not today's.
"""

import difflib
import json
import logging
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import NamedTuple, Protocol

from pipeline.config import PHOTON_URL

logger = logging.getLogger(__name__)

USER_AGENT = "memory-lane/1.0 (+https://github.com/linusaxel/memory-lane)"
PRECISION_M = {"house": 50, "poi": 50, "street": 200, "district": 1000}
# ponytail: one cutoff for every city; a per-city renumbering year if it matters.
NUMBERS_TRUSTED_FROM = 1900
# ponytail: a fixed radius around the model's guess; per-precision if it misfires.
MAX_KM_FROM_GUESS = 25


class Hit(NamedTuple):
    lat: float
    lng: float
    name: str | None
    street: str | None
    housenumber: str | None
    kind: str  # house | poi | street | district | city
    source: str  # becomes places.geocode_status


class Geocoder(Protocol):
    source: str
    handles: frozenset[str]  # "address", "venue"
    countries: frozenset[str] | None  # None: anywhere

    def search(self, text: str, locality: str | None, near: tuple | None) -> list[Hit]: ...


def _get_json(url: str):
    """None on any network or parse failure: the model's coordinate stays,
    which is what happened before any geocoder existed."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=10) as r:
            return json.load(r)
    except (
        urllib.error.URLError,
        TimeoutError,
        ValueError,
    ):
        # Kept exploded with a trailing comma on purpose.
        # See docs/10-decisions.md#except-a-b-stays-exploded
        logger.warning("Geocoder request failed, keeping the model's coordinate: %s", url)
        return None


def _q(text: str, locality: str | None) -> str:
    return f"{text}, {locality}" if locality else text


class Dawa:
    """Danish public addresses. Free, no key, Denmark only."""

    source = "dawa"
    handles = frozenset({"address"})
    countries = frozenset({"DK"})

    def search(self, text, locality, near):
        params = {"q": _q(text, locality), "fuzzy": "", "struktur": "mini", "per_side": 3}
        rows = _get_json(
            f"https://api.dataforsyningen.dk/adresser?{urllib.parse.urlencode(params)}"
        )
        return [
            Hit(r["y"], r["x"], None, r["vejnavn"], r["husnr"], "house", self.source)
            for r in rows or []
        ]


class Photon:
    """OpenStreetMap, worldwide. The public server asks for about one request a
    second; a self-hosted country extract is the same API (PHOTON_URL)."""

    source = "photon"
    handles = frozenset({"address", "venue"})
    countries = None
    _last = 0.0

    def search(self, text, locality, near):
        wait = 1.0 - (time.monotonic() - Photon._last)
        if wait > 0:
            time.sleep(wait)
        Photon._last = time.monotonic()
        params = {"q": _q(text, locality), "limit": 5}
        if near:
            params |= {"lat": near[0], "lon": near[1]}
        data = _get_json(f"{PHOTON_URL}/api?{urllib.parse.urlencode(params)}")
        hits = []
        for f in (data or {}).get("features", []):
            p = f["properties"]
            named = "poi" if p.get("name") else None
            kind = {"house": named or "house", "other": named, "street": "street"}.get(
                p.get("type")
            ) or ("district" if p.get("type") in ("district", "locality") else "city")
            lng, lat = f["geometry"]["coordinates"]
            hits.append(
                Hit(
                    lat,
                    lng,
                    p.get("name"),
                    p.get("street"),
                    p.get("housenumber"),
                    kind,
                    self.source,
                )
            )
        return hits


class Wikidata:
    """Notable places, including ones long gone (CBGB). CC0, so no credit owed.
    Searched on the bare name: "Vega Copenhagen" finds nothing."""

    source = "wikidata"
    handles = frozenset({"venue"})
    countries = None
    API = "https://www.wikidata.org/w/api.php"

    def search(self, text, locality, near):
        found = _get_json(
            f"{self.API}?"
            + urllib.parse.urlencode(
                {
                    "action": "wbsearchentities",
                    "search": text,
                    "language": "en",
                    "limit": 5,
                    "format": "json",
                }
            )
        )
        ids = [s["id"] for s in (found or {}).get("search", [])]
        if not ids:
            return []
        entities = _get_json(
            f"{self.API}?"
            + urllib.parse.urlencode(
                {
                    "action": "wbgetentities",
                    "ids": "|".join(ids),
                    "props": "claims|labels",
                    "languages": "en",
                    "format": "json",
                }
            )
        )
        hits = []
        for i in ids:
            e = (entities or {}).get("entities", {}).get(i, {})
            coord = e.get("claims", {}).get("P625")
            if not coord or "datavalue" not in coord[0]["mainsnak"]:
                continue
            v = coord[0]["mainsnak"]["datavalue"]["value"]
            label = e.get("labels", {}).get("en", {}).get("value")
            hits.append(Hit(v["latitude"], v["longitude"], label, None, None, "poi", self.source))
        return hits


GEOCODERS: list[Geocoder] = [Dawa(), Photon(), Wikidata()]


def _same(a: str | None, b: str | None) -> bool:
    return bool(a and b) and difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio() >= 0.85


# Words a venue's name gains or loses between the story and OSM: "Under Hylden"
# is "Café Under Hylden" on the map.
GENERIC = frozenset({"cafe", "café", "bar", "bodega", "pub", "restaurant", "the"})


def unbracket(name: str) -> str:
    """ "Bopa Bar" from "Bopa Bar (Nørrebro pub crawl)"."""
    return re.sub(r"\s*\([^)]*\)", "", name).strip()


def _same_venue(venue: str | None, hit: Hit) -> bool:
    """The same name, give or take spacing and generic words, or a point of
    interest's name inside the venue's: the model adds context ("Fri BikeShop
    Nørrebro"), the map never should ("Nørrebrogade" is not "Nørrebrogade
    Pizza"). Only a POI: "Nørrebro Parken" contains the district "Nørrebro"."""
    if not (venue and hit.name):
        return False
    a, b = (
        [w for w in re.findall(r"\w+", unbracket(n).lower()) if w not in GENERIC]
        for n in (venue, hit.name)
    )
    if not (a and b):
        return False
    return (hit.kind == "poi" and set(b) <= set(a)) or _same("".join(a), "".join(b))


def _km(a: tuple, b: tuple) -> float:
    (lat1, lng1), (lat2, lng2) = map(lambda p: (math.radians(p[0]), math.radians(p[1])), (a, b))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    )
    return 6371 * 2 * math.asin(math.sqrt(h))


def _split_address(address: str) -> tuple[str, str | None]:
    """("Blågårdsgade", "12") from "Blågårdsgade 12", and ("St Peter Street",
    "726") from "726 St Peter Street": the number may come first or last."""
    first = address.split(",")[0]
    number = re.search(r"\b(\d+)\s*[A-Za-z]?\b", first)
    street = re.sub(r"\b\d+\s*[A-Za-z]?\b", "", first).strip(" ,")
    return street, number.group(1) if number else None


def place(
    address: str | None,
    venue: str | None,
    locality: str | None,
    country: str | None,
    near: tuple | None,
    year: int | None,
) -> tuple[float, float, int, str] | None:
    """(lat, lng, precision_meters, source) for the first hit that survives the
    guard, or None. `near` is the model's own guess: wrong street, right city."""
    # A street with no number is a guess along its whole length; the venue,
    # if the map knows it, is a point.
    queries = []
    if address and _split_address(address)[1]:
        queries.append(("address", address))
    if venue:
        queries.append(("venue", venue))
    if address and not _split_address(address)[1]:
        queries.append(("address", address))

    for kind, text in queries:
        street, number = _split_address(text) if kind == "address" else (None, None)
        for g in GEOCODERS:
            if kind not in g.handles or (
                g.countries and (country or "").upper() not in g.countries
            ):
                continue
            for hit in g.search(text, locality, near):
                if hit.kind == "city":
                    continue
                if near and _km(near, (hit.lat, hit.lng)) > MAX_KM_FROM_GUESS:
                    continue
                if kind == "address":
                    if not _same(street, hit.street):
                        continue
                    digits = re.match(r"\d+", hit.housenumber or "")
                    house = number is not None and digits is not None and digits.group() == number
                    trusted = year is None or year >= NUMBERS_TRUSTED_FROM
                    return (
                        hit.lat,
                        hit.lng,
                        PRECISION_M["house" if house and trusted else "street"],
                        g.source,
                    )
                if not _same_venue(venue, hit):
                    continue
                return hit.lat, hit.lng, PRECISION_M[hit.kind], g.source
    return None
