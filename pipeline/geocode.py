"""Danish addresses to coordinates via DAWA. The model names the address;
this places it. See docs/10-decisions.md#dawa-places-danish-addresses.

Two traps found against the live API (2026-09-26), both guarded here:
- `fuzzy` always answers. "Nonexistentgade 999" came back as Vestergade 9,
  Nibe. A hit counts only if its street is the street we asked for.
- Copenhagen renumbered its houses in 1859: "Gothersgaden 330" in an 1856 paper
  is not Gothersgade 330 today. Before that, or with no date, the number is not
  trusted and the pin is street-level.
"""

import difflib
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

URL = "https://api.dataforsyningen.dk/adresser"
RENUMBERED = 1859
EXACT_M, STREET_M = 50, 200


def _street(s: str) -> str:
    # "aa" is the pre-1948 spelling of "å": Blaagaardsgade is Blågårdsgade.
    return s.lower().replace("aa", "å").strip()


def dawa(address: str, locality: str | None, year: int | None) -> tuple[float, float, int] | None:
    """(lat, lng, precision_meters) for a Danish address, or None if DAWA does
    not know the street. A network failure is None too: the model's coordinate
    stays, which is what happened before DAWA existed."""
    m = re.match(r"\s*([^\d,]+?)\s*(\d+)?\s*[A-Za-z]?\s*(?:,|$)", address)
    if not m:
        return None
    street, number = m.group(1), m.group(2)
    q = f"{address}, {locality}" if locality else address
    params = urllib.parse.urlencode({"q": q, "fuzzy": "", "struktur": "mini", "per_side": 1})
    try:
        with urllib.request.urlopen(f"{URL}?{params}", timeout=10) as r:
            hits = json.load(r)
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        logger.warning("DAWA failed for %r, keeping the model's coordinate: %s", address, e)
        return None
    if not hits:
        return None
    hit = hits[0]
    if difflib.SequenceMatcher(None, _street(street), _street(hit["vejnavn"])).ratio() < 0.85:
        logger.info("DAWA matched %r to %s, a different street", address, hit["betegnelse"])
        return None
    same_house = number is not None and re.match(r"\d+", hit["husnr"] or "")
    same_house = bool(same_house) and same_house.group() == number
    exact = same_house and year is not None and year >= RENUMBERED
    return hit["y"], hit["x"], EXACT_M if exact else STREET_M
