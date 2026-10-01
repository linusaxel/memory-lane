"""Server-rendered memory card, for the app sheet, the embed and any pasted
link. Why it is not JSON: docs/10-decisions.md#the-card-is-rendered-on-the-server.

It does not go through row_to_memory, so it has to remember the proximity gate
on its own. It once did not, and the whole corpus was one loop away.
tests/test_api_unlock.py holds it to that now.
"""

from html import escape

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import text

from api.gate import UNLOCK_RADIUS_METERS, is_locked, source_link, viewer_position
from api.media import media_url
from api.queries import COORDINATE_IS_UNIQUE
from pipeline.db import get_session

router = APIRouter()

CARD_QUERY = f"""
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
    -- The same expression the API uses, not a copy of it. is_locked() is
    -- shared between the two and would disagree with itself if these drifted,
    -- the comment saying so pointed at a file the constant had already moved
    -- out of, and there is now a third reason: idx_places_grid only serves
    -- this expression written exactly this way.
    {COORDINATE_IS_UNIQUE},
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
    """Where this memory's source opens. The rule lives in api/gate.py, because
    the API emits the same link and the two used to disagree about it."""
    return source_link(row)[0]


# Inline, because the card has to render standalone inside an iframe, a
# WebView and a link preview with no asset pipeline behind it.
FONT_HREF = (
    "https://fonts.googleapis.com/css2?"
    "family=Figtree:wght@400;500;600"
    "&family=Fraunces:opsz,wght,SOFT,WONK@9..144,400,100,0;9..144,700,100,1&display=swap"
)

# The palette is mobile/src/theme.ts, copied by hand because there are eleven
# values and no build step between TypeScript and Python. tests/test_palette.py
# fails if the two drift. Why these colours at all: docs/09-visual-design.md.
CARD_CSS = """
:root{--bg:#f7f4ee;--fg:#1c1917;--muted:#776e64;--rule:#e0d9cc;--accent:#a8350f}
@media (prefers-color-scheme:dark){
  :root{--bg:#161412;--fg:#f2ede4;--muted:#9a9086;--rule:#332e27;--accent:#f2703f}
}
*{box-sizing:border-box}
/* Soft Fraunces and Figtree, with stacks that hold on their own: a link
   preview bot fetches no fonts, and a card that collapses to Times is worse
   than one that was never restyled. `muted` is `faded`, not `inkFaint` - this
   sets 12px in it and inkFaint is 3.4:1 on paper. */
body{margin:0;background:var(--bg);color:var(--fg);
  font:400 16px/1.5 Fraunces,Georgia,"Times New Roman",serif;
  -webkit-font-smoothing:antialiased}
/* The card hugs its content and never stretches: this same markup is an iframe
   in the embed widget, where a card stretched to 100vh is a credit stranded at
   the bottom of a page of whitespace.
   Centred *only when there is room*, which is the standalone case - a pasted
   link opened in a browser used to be a postage stamp pinned to the top of an
   empty screen, and a screenshot of it is the product's one distribution
   channel. `safe center` is the whole trick: past the viewport height it
   degrades to start-aligned rather than clipping the top of a long card off
   the screen where no scroll can reach it. */
body{min-height:100svh;display:flex;flex-direction:column;
  justify-content:center;justify-content:safe center}
.card{max-width:34rem;width:100%;margin-inline:auto;padding:28px 24px;display:flex;
  flex-direction:column;gap:14px}
/* clamp() so the place name survives being scaled down to a thumbnail */
.place{font-size:clamp(22px,5.5vw,30px);font-weight:700;line-height:1.2;margin:0}
.when{font-family:Figtree,system-ui,-apple-system,"Segoe UI",sans-serif;
  font-size:12px;color:var(--muted);margin:0}
/* 19/31, the same size the app's sheet gives it, because it is the same
   sentence and it is the reason anybody opened this. */
.summary{font-size:19px;line-height:31px;margin:0}
/* A rule above, not a coloured bar down the left: elevation here is a hairline,
   and a left-border accent is the card tell this palette exists to avoid. */
.contrast{margin:0;padding-top:14px;border-top:1px solid var(--rule);
  font-size:16px;line-height:25px;color:var(--muted)}
/* Under the place name, as a byline: the first thing seen with the story,
   which is where the AI Act wants the label (docs/09 part 10). */
.credit{margin:0;
  font-family:Figtree,system-ui,-apple-system,"Segoe UI",sans-serif;
  font-size:12px;line-height:19px;color:var(--muted);display:flex;
  flex-wrap:wrap;gap:6px}
.credit a{color:var(--accent)}
/* A submitted memory usually is the photograph. Sized by aspect rather than a
   fixed height so a portrait phone shot is not cropped to a letterbox. */
.photo{width:100%;border-radius:14px;display:block;max-height:60vh;object-fit:cover}
.layer{display:inline-block;
  font-family:Figtree,system-ui,-apple-system,"Segoe UI",sans-serif;
  font-size:13px;font-weight:600;color:var(--muted)}
@media (max-width:360px){.card{padding:18px 16px}.summary{font-size:17px;line-height:28px}}
"""


def preview_tags(place: str, description: str) -> str:
    """What a pasted link looks like in a chat window.

    **Every preview is the locked card**, and that is correct rather than a
    limitation: a crawler has no position, so `is_locked` withholds the summary
    from it exactly as it would from a person standing somewhere else. The
    description a link unfurls with is therefore the refusal - "something
    happened here, stand where it happened" - which is the pitch anyway.

    No `og:image`. The photograph is behind the same gate, so the only card that
    has one to offer is the one a crawler can never fetch.

    Takes RAW text and escapes it here, once. Passing the body's already-escaped
    strings in was the first version and it double-escaped: a title rendered as
    `Katz&#x27;s Delicatessen`, literally, in every unfurl.
    """
    tags = {
        "og:title": place,
        "og:description": description,
        "og:type": "article",
        "og:site_name": "Memory Lane",
        "twitter:card": "summary",
    }
    return "\n".join(
        f'<meta property="{key}" content="{escape(value, quote=True)}">'
        for key, value in tags.items()
    )


def render_card(row) -> str:
    place = escape(row.place_name or "Unknown place")
    summary = escape(row.summary or "")
    credit = escape(credit_line(row))
    when = format_happened(row.happened_at, row.happened_precision)
    href = source_href(row)

    when_html = f'<p class="when">{escape(when)}</p>' if when else ""
    photo_path = getattr(row, "photo_path", None)
    photo_html = ""
    if photo_path:
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
{preview_tags(row.place_name or "Unknown place", row.summary or "")}
<link rel="stylesheet" href="{FONT_HREF}">
<style>{CARD_CSS}</style>
</head><body>
<article class="card">
  <span class="layer">{escape(row.layer or "historical")}</span>
  <h1 class="place">{place}</h1>
  <p class="credit">{credit_html}</p>
  {when_html}
  {photo_html}
  <p class="summary">{summary}</p>
  {contrast_html}
</article>
</body></html>"""


def render_locked_card(row, radius_meters: int) -> str:
    """The same card with its middle withheld. Deliberately still a card: the
    credit line survives, because attribution is the point of rendering this
    server-side and is no less owed for a memory you have not earned yet."""
    place = escape(row.place_name or "Unknown place")
    credit = escape(credit_line(row))

    label = "locked"
    withheld = f"Something happened here. Stand within {radius_meters} m of it to read it."

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{place} - Memory Lane</title>
<meta name="color-scheme" content="light dark">
{preview_tags(row.place_name or "Unknown place", withheld)}
<link rel="stylesheet" href="{FONT_HREF}">
<style>{CARD_CSS}</style>
</head><body>
<article class="card">
  <span class="layer">{label}</span>
  <h1 class="place">{place}</h1>
  <p class="credit">{credit}</p>
  <p class="summary">{withheld}</p>
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
    with get_session() as session:
        row = session.execute(text(CARD_QUERY), {"memory_id": memory_id}).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    if is_locked(row, viewer_position(at_lat, at_lng)):
        return HTMLResponse(render_locked_card(row, UNLOCK_RADIUS_METERS))

    return HTMLResponse(render_card(row))
