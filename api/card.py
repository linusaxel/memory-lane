"""Server-rendered memory card.

One template, three consumers: the app sheet, the Phase 2 embed widget, and any
pasted link. Rendered here rather than in the client because the attribution is
the legal posture - a client that assembles the card from JSON can drop the
credit line, and this is the corpus of someone else's archive. Server-rendered
means the credit ships welded to the content.

Design constraints live in mobile/UI.md; the ones that bind here are that place
name and attribution stay legible at thumbnail size, and that the card is
correct in both colour schemes.

This route is gated like every other one that can emit a summary. It was not,
for a while: /v1/memories/{id}/card rendered a locked memory in full, and since
ids are sequential the whole corpus was one loop away. F7's rule - "a client-side
gate is not a gate" - is about exactly this, and the card was the side door,
because it does not go through row_to_memory and had to be remembered separately.
It is remembered now, and tests/test_api_unlock.py holds it to it.
"""

from html import escape

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import text

from pipeline.db import get_session

router = APIRouter()

CARD_QUERY = """
SELECT
    m.id,
    m.summary,
    m.layer,
    m.happened_at,
    m.happened_precision,
    m.attribution,
    m.source_url,
    m.contrast_note,
    m.timestamp_start,
    p.name AS place_name,
    p.precision_meters,
    c.source_name,
    ST_Y(p.coordinates::geometry) AS lat,
    ST_X(p.coordinates::geometry) AS lng,
    -- Kept identical to api/main.py's COORDINATE_IS_UNIQUE, including the
    -- exclusion of user-submitted places. is_locked() is shared between the two
    -- and would disagree with itself if these drifted.
    (
        SELECT COUNT(*) = 1 FROM places p2
        WHERE ST_SnapToGrid(p2.coordinates::geometry, 0.0001)
            = ST_SnapToGrid(p.coordinates::geometry, 0.0001)
          AND NOT EXISTS (
              SELECT 1 FROM memories m2 WHERE m2.place_id = p2.id AND m2.user_id IS NOT NULL
          )
    ) AS coordinate_is_unique,
    m.user_id,
    au.display_name AS author_name,
    (
        SELECT md.path FROM media md
        WHERE md.memory_id = m.id AND md.kind = 'photo'
        ORDER BY md.id LIMIT 1
    ) AS photo_path,
    c.title AS content_title,
    c.url AS content_url
FROM memories m
JOIN places p ON m.place_id = p.id
LEFT JOIN content c ON m.content_id = c.id
LEFT JOIN users au ON m.user_id = au.id
WHERE m.id = :memory_id AND NOT m.hidden
"""


def format_happened(happened_at, precision: str | None) -> str | None:
    """A date is only as specific as the precision claims.

    Rendering 1893-01-01 as "1 January 1893" invents a day the source never
    gave. Postgres stores a full date whatever the precision, so the precision
    column is the only thing that knows how much of it is real.
    """
    if happened_at is None:
        return None
    if precision == "decade":
        return f"{happened_at.year // 10 * 10}s"
    if precision == "year" or precision is None:
        return str(happened_at.year)
    if precision == "month":
        return happened_at.strftime("%B %Y")
    return happened_at.strftime("%-d %B %Y")


def credit_line(row) -> str:
    """Never empty. An uncredited card is the one thing this endpoint exists to
    prevent, so fall back through every field that could name a source before
    admitting we do not know.

    The publisher outranks the episode title. "Tuesdays with Stories" tells a
    reader who is talking; "Ep 512 - A Sauna Too Far" does not, and a card that
    leaves the screen is read by people who have no idea what either is.
    """
    if row.attribution:
        return row.attribution

    source = getattr(row, "source_name", None)
    if source and row.content_title:
        return f"{source} — {row.content_title}"
    if source:
        return source

    if row.content_title:
        return row.content_title

    # A submitted memory has no content row at all, so the person who filed it
    # is the credit. Below the archive's attribution and the publisher, because
    # those are claims about provenance and this is a signature.
    if getattr(row, "user_id", None) is not None:
        return getattr(row, "author_name", None) or "Anonymous"

    if row.content_url:
        return row.content_url
    return "Source unknown"


def source_href(row) -> str | None:
    """An archival source_url is a document and gets linked as-is. Only a video
    takes a ?t= offset, and only YouTube is known to honour one - the same rule
    row_to_memory applies in api/main.py."""
    if row.source_url:
        return row.source_url
    if not row.content_url:
        return None
    is_youtube = "youtube.com" in row.content_url or "youtu.be" in row.content_url
    # `is not None`, not truthiness: timestamp_start of 0.0 is the start of the
    # video, not a missing value.
    if is_youtube and row.timestamp_start is not None:
        sep = "&" if "?" in row.content_url else "?"
        return f"{row.content_url}{sep}t={int(row.timestamp_start)}"
    return row.content_url


# Inline, because the card has to render standalone inside an iframe, a
# WebView and a link preview with no asset pipeline behind it.
CARD_CSS = """
:root{--bg:#fff;--fg:#18181b;--muted:#71717a;--rule:#e4e4e7;--accent:#dc2626}
@media (prefers-color-scheme:dark){
  :root{--bg:#18181b;--fg:#fafafa;--muted:#a1a1aa;--rule:#3f3f46;--accent:#f87171}
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
  font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
  -webkit-font-smoothing:antialiased}
/* Hugs its content rather than filling the viewport: this same markup is an
   iframe in the embed widget and a link preview, where 100vh is a page of
   whitespace with a credit stranded at the bottom. */
.card{max-width:34rem;margin:0 auto;padding:28px 24px;display:flex;
  flex-direction:column;gap:14px}
/* clamp() so the place name survives being scaled down to a thumbnail */
.place{font-size:clamp(22px,5.5vw,30px);font-weight:700;letter-spacing:-.02em;
  line-height:1.15;margin:0}
.when{font-size:14px;color:var(--muted);margin:0}
.summary{font-size:17px;line-height:1.6;margin:0}
.contrast{margin:0;padding-left:12px;border-left:3px solid var(--accent);
  font-size:15px;color:var(--muted)}
.credit{margin-top:4px;padding-top:14px;border-top:1px solid var(--rule);
  font-size:13px;color:var(--muted);display:flex;flex-wrap:wrap;gap:6px}
.credit a{color:inherit}
/* A submitted memory usually is the photograph. Sized by aspect rather than a
   fixed height so a portrait phone shot is not cropped to a letterbox. */
.photo{width:100%;border-radius:6px;display:block;max-height:60vh;object-fit:cover}
.layer{display:inline-block;font-size:11px;text-transform:uppercase;
  letter-spacing:.08em;color:var(--muted)}
@media (max-width:360px){.card{padding:18px 16px}.summary{font-size:16px}}
"""


def render_card(row) -> str:
    place = escape(row.place_name or "Unknown place")
    summary = escape(row.summary or "")
    credit = escape(credit_line(row))
    when = format_happened(row.happened_at, row.happened_precision)
    href = source_href(row)

    when_html = f'<p class="when">{escape(when)}</p>' if when else ""
    # Imported here for the same cycle reason as the route below; api.media has
    # no dependency on this module, but keeping both imports in one place is
    # less surprising than one at the top and one inside a function.
    photo_path = getattr(row, "photo_path", None)
    photo_html = ""
    if photo_path:
        from api.media import media_url

        photo_html = f'<img class="photo" src="{escape(media_url(photo_path), quote=True)}" alt="">'

    contrast_html = (
        f'<p class="contrast">{escape(row.contrast_note)}</p>' if row.contrast_note else ""
    )
    # The credit is plain text when there is nowhere to link; it is never absent.
    credit_html = f'<a href="{escape(href, quote=True)}">{credit}</a>' if href else credit

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{place} - Memory Lane</title>
<meta name="color-scheme" content="light dark">
<style>{CARD_CSS}</style>
</head><body>
<article class="card">
  <span class="layer">{escape(row.layer or "historical")}</span>
  <h1 class="place">{place}</h1>
  {when_html}
  {photo_html}
  <p class="summary">{summary}</p>
  {contrast_html}
  <p class="credit">{credit_html}</p>
</article>
</body></html>"""


def render_locked_card(row, radius_meters: int) -> str:
    """The same card with its middle withheld. Deliberately still a card: the
    credit line survives, because attribution is the point of rendering this
    server-side and is no less owed for a memory you have not earned yet."""
    place = escape(row.place_name or "Unknown place")
    credit = escape(credit_line(row))

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{place} - Memory Lane</title>
<meta name="color-scheme" content="light dark">
<style>{CARD_CSS}</style>
</head><body>
<article class="card">
  <span class="layer">locked</span>
  <h1 class="place">{place}</h1>
  <p class="summary">Something happened here. Stand within {radius_meters} m of it
    to read it.</p>
  <p class="credit">{credit}</p>
</article>
</body></html>"""


@router.get("/v1/memories/{memory_id}/card", response_class=HTMLResponse)
def memory_card(
    memory_id: int,
    at_lat: float | None = Query(
        None, ge=-90, le=90, description="Where you actually are; unlocks this card if near"
    ),
    at_lng: float | None = Query(
        None, ge=-180, le=180, description="Where you actually are; unlocks this card if near"
    ),
):
    """One memory, rendered. See the module docstring for why this is not JSON.

    A gated memory renders as a locked card - place and invitation, no summary -
    unless a position inside the radius is supplied. The embed relies on that:
    "there is a memory here, go and stand in it" is a perfectly good thing for
    somebody else's tourism page to say, and is the only thing it may say.
    """
    # Imported here rather than at module scope: api.main imports this router,
    # so a top-level import would be a cycle.
    from api.main import UNLOCK_RADIUS_METERS, is_locked, viewer_position

    with get_session() as session:
        row = session.execute(text(CARD_QUERY), {"memory_id": memory_id}).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    if is_locked(row, viewer_position(at_lat, at_lng)):
        return HTMLResponse(render_locked_card(row, UNLOCK_RADIUS_METERS))

    return HTMLResponse(render_card(row))
