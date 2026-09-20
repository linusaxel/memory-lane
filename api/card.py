"""Server-rendered memory card.

One template, three consumers: the app sheet, the Phase 2 embed widget, and any
pasted link. Rendered here rather than in the client because the attribution is
the legal posture - a client that assembles the card from JSON can drop the
credit line, and this is the corpus of someone else's archive. Server-rendered
means the credit ships welded to the content.

Design constraints live in mobile/UI.md; the ones that bind here are that place
name and attribution stay legible at thumbnail size, and that the card is
correct in both colour schemes.
"""

from html import escape

from fastapi import APIRouter, HTTPException
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
    c.title AS content_title,
    c.url AS content_url
FROM memories m
JOIN places p ON m.place_id = p.id
JOIN content c ON m.content_id = c.id
WHERE m.id = :memory_id
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
    admitting we do not know."""
    if row.attribution:
        return row.attribution
    if row.content_title:
        return row.content_title
    if row.content_url:
        return row.content_url
    return "Source unknown"


def source_href(row) -> str | None:
    if row.source_url:
        return row.source_url
    if row.content_url and row.timestamp_start:
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
  <p class="summary">{summary}</p>
  {contrast_html}
  <p class="credit">{credit_html}</p>
</article>
</body></html>"""


@router.get("/v1/memories/{memory_id}/card", response_class=HTMLResponse)
def memory_card(memory_id: int):
    """One memory, rendered. See the module docstring for why this is not JSON."""
    with get_session() as session:
        row = session.execute(text(CARD_QUERY), {"memory_id": memory_id}).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    return HTMLResponse(render_card(row))
