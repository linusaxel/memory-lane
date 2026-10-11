"""What a new memory's story doesn't tell: who its people were, more of their
words, then against now, a surprise or two, and pictures of the place.

    python -m pipeline.enrich --memory 42   # one, printed, the memory untouched (bills)

Aggregation runs it on each new content's memories; there is no backfill
(docs/10, *A memory is enriched when it is made*). The model researches with
web search and fetch, and code keeps only what a page we fetched ourselves
says: every item carries a passage copied from its page, and an item whose
passage isn't on that page is dropped, as `extract.grounded` drops a quote.
Pictures come by code, never from the model: Wikimedia Commons under a
licence that lets us show them with a credit, and the source page's own,
hotlinked and never copied (docs/10, *The sources' legal footing*).

Bills: one short pick call a memory. The research (web search at
ENRICH_MAX_SEARCHES, about $0.01 a search) now runs only for a thin record's
seed (docs/10, *Research waits until it is served*). Each reply is stored
in extraction_chunks, so `python -m pipeline.batch` sends them at half price.
"""

import argparse
import json
import logging
import re
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from html.parser import HTMLParser

from sqlalchemy import text

from pipeline import extract, geocode
from pipeline.config import ENRICH_MAX_SEARCHES, EXTRACTION_MODEL
from pipeline.extract import _sha256, _squash, _stored_request, log_cache, reply_text, store

logger = logging.getLogger(__name__)

RESEARCH_PROMPT = """You research a short story told at a place, for a reader standing
there who has just read it. Search the web, read the pages you find, and report
what the story does not tell, each with the page's URL and a passage copied
exactly from that page (at most 30 words) that shows it:

- people: each real, public person in the story (an artist, a king, a band, a
  known writer): who they were, in one line, their birth and death years, and
  a page about them. Leave out private people: anyone known only from this
  story gets nothing.
- quotes: words someone said or wrote about this event, this place, or this
  person's time here, copied exactly from the page, at most 40 words, with who
  said it and when.
- then and now: what stood or happened here then, what is here now, and the
  turn between them ("closed in 1986", "regilded in 2024").
- asides: one to three surprising facts about this exact spot, or about the
  people in the story, that the story does not tell. Not the city's general
  history.

Only what the pages say. Leave out anything you can't copy a passage for; an
empty section is fine. Don't retell the story."""

SEED_PROMPT = """The text is a short record found at a place: a plaque's
inscription, a line in an archive. Research the story behind it: what happened
here, who the people were, why it mattered then, and the human detail or the
surprise a stranger standing here would want to know. Search the web, read the
pages you find, and report each finding with the page's URL and a passage
copied exactly from that page (at most 80 words) that shows it. Only what the
pages say; leave out anything you can't copy a passage for. If there is no
story behind the record, say so."""

STRUCTURE_PROMPT = """The text is research notes about a story told at a place. Put
them in the fields, copying each URL and passage exactly as the notes give
them. Leave out anything the notes give without a URL and a passage. Write
`who`, `then`, `now` and `text` as plain sentences of your own, past tense
for the past, for a reader standing at the place."""

_ITEM = {"url": {"type": "string"}, "passage": {"type": "string"}}
_NULLABLE_INT = {"anyOf": [{"type": "integer"}, {"type": "null"}]}


def _items(fields: dict) -> dict:
    props = fields | _ITEM
    return {
        "type": "array",
        "items": {
            "type": "object",
            "properties": props,
            "required": list(props),
            "additionalProperties": False,
        },
    }


STRUCTURE_SCHEMA = {
    "type": "object",
    "properties": {
        "people": _items(
            {
                "name": {"type": "string"},
                "who": {"type": "string"},
                "born": _NULLABLE_INT,
                "died": _NULLABLE_INT,
            }
        ),
        "quotes": _items(
            {"text": {"type": "string"}, "by": {"type": "string"}, "when": {"type": "string"}}
        ),
        "then_now": _items({"then": {"type": "string"}, "now": {"type": "string"}}),
        "asides": _items({"text": {"type": "string"}}),
    },
    "required": ["people", "quotes", "then_now", "asides"],
    "additionalProperties": False,
}

PICK_PROMPT = """The text is a place, the story told there, then numbered pictures,
each with its caption and date: first the story's own source page's, marked
[source], then Wikimedia Commons pictures taken near it. Pick up to four, best
first: a picture of the moment itself (the people in the story, there, then)
comes first; then this place as it was; then it as it is.
Before you keep a picture whose caption names a person or a band, find that
name in the story. Not there means it is another night: leave it out, however
famous (a story of Deep Purple gets no Led Zeppelin photo). Leave out pictures of other buildings, of
maps, of people who are not public figures, logos, adverts, and anything you
can't tell is this place or this story. An empty list is a fine answer."""

PICK_SCHEMA = {
    "type": "object",
    "properties": {"pick": {"type": "array", "items": {"type": "integer"}}},
    "required": ["pick"],
    "additionalProperties": False,
}

COMMONS = "https://commons.wikimedia.org/w/api.php"
# Free to show with a credit. Anything else (non-commercial, no derivatives,
# fair use) is not ours to show in a paid app.
FREE = ("public domain", "pd", "cc0", "cc by", "cc-by", "attribution")
# "CC BY-NC-SA 4.0" starts with "cc by" too.
UNFREE = re.compile(r"\bnc\b|\bnd\b|non-?commercial|no ?deriv", re.I)
PICTURE_METERS = 60
SOURCE_PICTURES = 30
# A logo, icon or tracking pixel is no picture of the story.
NOT_A_PICTURE = re.compile(r"logo|icon|sprite|avatar|pixel|badge|spinner|flags?/|\.svg(\?|$)", re.I)
PHOTO = re.compile(r"\.(jpe?g|png|webp)(\?|$)", re.I)
YEAR = re.compile(r"\b(1[6-9]\d\d|20\d\d)\b")
PAGE_BYTES = 3_000_000


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self._skip = [], 0

    def handle_starttag(self, tag, attrs):
        self._skip += tag in ("script", "style")

    def handle_endtag(self, tag):
        self._skip -= tag in ("script", "style") and self._skip > 0

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def page_html(url: str) -> str | None:
    """The page as fetched by us, or None when it doesn't answer. A PDF or an
    image is no page for this."""
    request = urllib.request.Request(url, headers={"User-Agent": geocode.USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=20) as r:
            if "html" not in r.headers.get("Content-Type", "html"):
                return None
            return r.read(PAGE_BYTES).decode(r.headers.get_content_charset() or "utf-8", "replace")
    except (
        OSError,
        ValueError,
    ):
        return None


def page_text(url: str) -> str | None:
    """The page's words, squashed as extract._squash squashes a chunk."""
    raw = page_html(url)
    if raw is None:
        return None
    parser = _Text()
    parser.feed(raw)
    return _squash(" ".join(parser.parts))


class _Images(HTMLParser):
    """Each <img> with its alt text, and the <figcaption> of the figure it sits in."""

    def __init__(self):
        super().__init__()
        self.found, self._figure, self._caption = [], None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "figure":
            self._figure = []
        elif tag == "figcaption" and self._figure is not None:
            self._caption = []
        elif tag == "img":
            srcset = a.get("srcset") or a.get("data-srcset") or ""
            srcset = [s.split()[0] for s in srcset.split(",") if s.strip()]
            # A lazy-loading page puts the real picture in a data- attribute
            # (data-src, data-flickity-lazyload) and a placeholder in src.
            lazy = [v for k, v in attrs if k.startswith("data-") and v and PHOTO.search(v)]
            width = a.get("width") or ""
            item = {
                "src": srcset[-1] if srcset else (lazy or [a.get("src") or ""])[0],
                "alt": a.get("alt") or "",
                "small": not srcset and width.isdigit() and int(width) < 300,
            }
            self.found.append(item)
            if self._figure is not None:
                self._figure.append(item)

    def handle_data(self, data):
        if self._caption is not None:
            self._caption.append(data)

    def handle_endtag(self, tag):
        if tag == "figcaption" and self._caption is not None:
            for item in self._figure or []:
                item["caption"] = " ".join("".join(self._caption).split())
            self._caption = None
        elif tag == "figure":
            self._figure = None


def free(license_: str) -> bool:
    return license_.lower().startswith(FREE) and not UNFREE.search(license_)


def name(src: str) -> str:
    return urllib.parse.unquote(src.rsplit("/", 1)[-1].split("?")[0].split(".")[0])


def source_pictures(url: str | None, credit: str, fetch=page_html) -> list[dict]:
    """The source page's own pictures, as Commons ones are listed. Only the URL
    is kept: the app loads it from the source, credited and linked."""
    if not url or not url.startswith("http") or "youtu" in url or url.lower().endswith(".pdf"):
        return []
    raw = fetch(url.split("#")[0])
    if not raw:
        return []
    parser = _Images()
    parser.feed(raw)
    pictures = []
    for img in parser.found:
        src = urllib.parse.urljoin(url, img["src"])
        if not src.startswith("http") or img["small"] or NOT_A_PICTURE.search(src):
            continue
        pictures.append(
            {
                "url": src,
                "thumb": src,
                "page": url,
                # A file name ("08briannielsen") is caption enough to pick by.
                "caption": (img.get("caption") or img["alt"] or name(src))[:300],
                "year": None,
                "author": credit,
                "license": f"© {credit}",
                "source": True,
            }
        )
    return list({p["url"]: p for p in pictures}.values())[:SOURCE_PICTURES]


def verified(found: dict, fetch=page_text) -> dict:
    """Only the items whose passage is on their page, and a person only where
    the page names them; a quote has to be there word for word too."""
    pages: dict[str, str | None] = {}

    def on_page(url: str, *texts: str) -> bool:
        if url not in pages:
            pages[url] = fetch(url) if url.startswith(("http://", "https://")) else None
        page = pages[url]
        return bool(page) and all((t := _squash(x)) and t in page for x in texts)

    kept = {
        "people": [p for p in found["people"] if on_page(p["url"], p["passage"], p["name"])],
        "quotes": [q for q in found["quotes"] if on_page(q["url"], q["passage"], q["text"])],
        "then_now": [t for t in found["then_now"] if on_page(t["url"], t["passage"])],
        "asides": [a for a in found["asides"] if on_page(a["url"], a["passage"])],
    }
    dropped = sum(len(found[k]) - len(v) for k, v in kept.items())
    if dropped:
        logger.info("Dropped %s enrichment items whose passage was not on their page", dropped)
    return kept


# Research and what follows it are stored in extraction_chunks under this index.
INDEX = -5


def research(
    session, client, content_id: int, place: str, summary: str, prompt: str = RESEARCH_PROMPT
) -> str | None:
    """The model's notes from the web, or None for no answer. Stored as
    `extract._stored_request` stores a reply, so it is paid for once and a
    batch pass collects it (pipeline/batch.py)."""
    params = dict(
        model=EXTRACTION_MODEL,
        max_tokens=16000,
        system=prompt,
        messages=[{"role": "user", "content": f"Place: {place}\n\nStory: {summary}"}],
        # Searching and copying passages needs little thought, and thinking
        # at the default effort was the bulk of this call's output.
        output_config={"effort": "low"},
        # Each search or page read is another turn over everything before
        # it; with caching on, those turns read the earlier ones at 10%.
        cache_control={"type": "ephemeral"},
        tools=[
            {"type": "web_search_20260318", "name": "web_search", "max_uses": ENRICH_MAX_SEARCHES},
            {"type": "web_fetch_20260318", "name": "web_fetch", "max_uses": ENRICH_MAX_SEARCHES},
        ],
    )
    key = _sha256(f"{content_id}\0{json.dumps(params, sort_keys=True)}")
    notes = session.execute(
        text("SELECT response FROM extraction_chunks WHERE request_hash = :k"), {"k": key}
    ).scalar()
    if notes is not None:
        return notes.strip() or None
    if extract.COLLECT is not None:
        if extract.COLLECT.stage.setdefault(content_id, prompt) == prompt:
            extract.COLLECT.requests[key] = {
                "params": params,
                "content_id": content_id,
                "chunk_index": INDEX,
                "prompt_hash": _sha256(prompt),
                "stage": "research",
            }
        return None
    try:
        response = client.messages.create(**params)
    except Exception:
        logger.exception("Research failed for %s", place)
        return None
    log_cache(response)
    notes = reply_text(response)
    if notes is not None:
        store(session, key, content_id, INDEX, _sha256(prompt), notes)
    return (notes or "").strip() or None


def structured(session, client, content_id: int, notes: str | None) -> dict | None:
    """The notes in STRUCTURE_SCHEMA, only what their pages say; None for no answer."""
    raw = notes and _stored_request(
        session,
        client,
        content_id,
        INDEX,
        STRUCTURE_PROMPT,
        notes,
        STRUCTURE_SCHEMA,
        max_tokens=8000,
    )
    try:
        return verified(json.loads(raw)) if raw else None
    except (
        ValueError,
        KeyError,
    ):
        return None


def _commons(params: dict) -> dict:
    found = geocode._get_json(f"{COMMONS}?" + urllib.parse.urlencode(params | {"format": "json"}))
    return found or {}


def _meta(info: dict, key: str) -> str:
    value = info.get("extmetadata", {}).get(key, {}).get("value", "")
    parser = _Text()
    parser.feed(str(value))
    return " ".join("".join(parser.parts).split())


def pictures_near(lat: float, lng: float, venue: str, locality: str | None) -> list[dict]:
    """Freely licensed Commons pictures geotagged by the pin or named for the
    venue in its city, with what a credit line needs."""
    near = _commons(
        {
            "action": "query",
            "list": "geosearch",
            "gscoord": f"{lat}|{lng}",
            "gsradius": PICTURE_METERS,
            "gsnamespace": 6,
            "gslimit": 30,
        }
    )
    named = _commons(
        {
            "action": "query",
            "list": "search",
            "srsearch": f'"{venue}" {locality or ""}'.strip(),
            "srnamespace": 6,
            "srlimit": 20,
        }
    )
    titles = list(
        dict.fromkeys(
            [g["title"] for g in near.get("query", {}).get("geosearch", [])]
            + [s["title"] for s in named.get("query", {}).get("search", [])]
        )
    )
    pictures = []
    for i in range(0, len(titles), 50):
        found = _commons(
            {
                "action": "query",
                "titles": "|".join(titles[i : i + 50]),
                "prop": "imageinfo",
                "iiprop": "url|extmetadata|mime",
                "iiurlwidth": 1024,
            }
        )
        for page in found.get("query", {}).get("pages", {}).values():
            info = (page.get("imageinfo") or [{}])[0]
            license_ = _meta(info, "LicenseShortName")
            if not info.get("mime", "").startswith("image/") or not free(license_):
                continue
            pictures.append(
                {
                    "url": info.get("url"),
                    "thumb": info.get("thumburl"),
                    "page": info.get("descriptionurl"),
                    "caption": _meta(info, "ImageDescription")[:300] or page["title"][5:],
                    "year": (y := YEAR.search(_meta(info, "DateTimeOriginal"))) and y[0],
                    "author": _meta(info, "Artist")[:120],
                    "license": license_,
                }
            )
    return pictures


def pick(session, client, content_id: int, place: str, summary: str, pictures: list[dict]):
    """Up to four of `pictures`, best first; None while a batch pass waits on it."""
    if not pictures:
        return []
    listed = "\n".join(
        f"{i}. {'[source] ' if p.get('source') else ''}{p['caption']} ({p['year'] or 'undated'})"
        for i, p in enumerate(pictures)
    )
    user = f"Place: {place}\n\nStory: {summary}\n\n{listed}"
    raw = _stored_request(session, client, content_id, INDEX, PICK_PROMPT, user, PICK_SCHEMA)
    if raw is None and extract.COLLECT is not None:
        return None
    try:
        chosen = json.loads(raw)["pick"] if raw else []
    except (
        ValueError,
        KeyError,
    ):
        return []
    return [pictures[i] for i in dict.fromkeys(chosen) if 0 <= i < len(pictures)][:4]


def enrich(
    session,
    client,
    content_id: int,
    place: str,
    summary: str,
    lat,
    lng,
    venue: str | None,
    locality: str | None,
    source_url: str | None = None,
    credit: str | None = None,
) -> dict | None:
    """The memory's pictures, or None while the pick waits on a batch pass.
    No web research: its people, quotes and asides are not served, and were
    most of the bill (docs/10, *Research waits until it is served*)."""
    pictures = []
    try:
        found_pictures = source_pictures(source_url, credit or "the source")
        if lat is not None:
            found_pictures += pictures_near(lat, lng, venue or place, locality)
        pictures = pick(session, client, content_id, place, summary, found_pictures)
    except Exception:
        logger.exception("Pictures failed for %s", place)
    if pictures is None:
        return None
    return {"pictures": pictures, "at": datetime.now(UTC).isoformat(timespec="seconds")}


def seed(session, client, content_id: int, place: str, record: str) -> str | None:
    """What cited pages say about a thin record, one passage a line with its
    URL, to extract from beside it; empty when nothing checks out
    (docs/10, *A thin source is a lead*), None while a batch pass waits on it."""
    notes = research(session, client, content_id, place, record, SEED_PROMPT)
    found = structured(session, client, content_id, notes) or {}
    if extract.COLLECT is not None and content_id in extract.COLLECT.stage:
        return None
    lines = (f'From {i["url"]}: "{i["passage"]}"' for items in found.values() for i in items)
    return "\n".join(dict.fromkeys(lines))


UNENRICHED = """
    SELECT m.id, m.content_id, p.name, p.venue, p.locality, m.summary,
           COALESCE(m.source_url, c.url) AS source_url,
           COALESCE(c.source_name, m.attribution) AS credit,
           ST_Y(p.coordinates::geometry) AS lat, ST_X(p.coordinates::geometry) AS lng
    FROM memories m JOIN places p ON p.id = m.place_id
    LEFT JOIN content c ON c.id = m.content_id
    WHERE m.enrichment IS NULL AND m.user_id IS NULL AND NOT m.hidden
      AND m.content_id = :content_id
    ORDER BY m.id
"""


def _args(r) -> tuple:
    return r.name, r.summary, r.lat, r.lng, r.venue, r.locality, r.source_url, r.credit


def enrich_memories(session, client, content_id: int) -> dict:
    """Enrich one content's new memories; return {memory_id: enrichment}."""
    done = {}
    for r in session.execute(text(UNENRICHED), {"content_id": content_id}).fetchall():
        found = enrich(session, client, content_id, *_args(r))
        if found is None:
            continue
        session.execute(
            text("UPDATE memories SET enrichment = CAST(:e AS JSONB) WHERE id = :id"),
            {"e": json.dumps(found), "id": r.id},
        )
        session.commit()
        done[r.id] = found
        time.sleep(1)  # Commons' and the pages' fair use
    return done


def main():
    import anthropic

    from pipeline.config import ANTHROPIC_API_KEY
    from pipeline.db import get_session

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--memory", type=int, required=True, help="one memory, by id")
    args = parser.parse_args()
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    with get_session() as session:
        r = session.execute(
            text(
                UNENRICHED.replace("m.enrichment IS NULL", "TRUE").replace(
                    "m.content_id = :content_id", "m.id = :id"
                )
            ),
            {"id": args.memory},
        ).one()
        found = enrich(session, client, r.content_id, *_args(r))
    print(json.dumps(found, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
