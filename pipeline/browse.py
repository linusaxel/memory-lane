"""Every memory and all of it, in a browser, for us.

Ungated on purpose, so it is a local tool and never a route on the API: it
reads the database directly and binds to 127.0.0.1 only. Hidden memories are
shown, marked. Type in the box to filter; click a row for everything else.

    python -m pipeline.browse            # http://127.0.0.1:8765
    python -m pipeline.browse --port 9000
"""

import argparse
import json
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from sqlalchemy import text

from api.card import source_href
from pipeline.db import get_session

QUERY = """
SELECT m.id, m.summary, m.quote, m.quote_by, m.tags, m.layer, m.hidden,
       m.walk_score, m.extraction_confidence, m.happened_at, m.happened_precision,
       m.contrast_note, m.attribution, m.source_url, m.timestamp_start,
       m.links, m.enrichment, m.created_at,
       p.name AS place, ST_Y(p.coordinates::geometry) AS lat, ST_X(p.coordinates::geometry) AS lng,
       c.title, c.source_name, c.url AS content_url
FROM memories m
JOIN places p ON p.id = m.place_id
LEFT JOIN content c ON c.id = m.content_id
ORDER BY m.id DESC
"""

PAGE = """<!doctype html><meta charset="utf-8"><title>Memories</title>
<style>
body{{font:14px system-ui;margin:16px;background:#fff;color:#222}}
input{{width:100%;padding:8px;font-size:16px;box-sizing:border-box;position:sticky;top:0}}
details{{border-bottom:1px solid #ddd;padding:6px 0}}
summary{{cursor:pointer}} .hidden{{opacity:.45}} .meta{{color:#777}}
.body{{white-space:pre-wrap;max-width:70ch;margin:8px 0}}
pre{{background:#f5f5f5;padding:8px;overflow:auto;font-size:12px}}
</style>
<input id=q placeholder="Filter {count} memories (any text, e.g. a place, tag, 'hidden', 'score 10')" autofocus>
{rows}
<script>
q.oninput=()=>{{const t=q.value.toLowerCase();for(const d of document.querySelectorAll('details'))d.style.display=d.textContent.toLowerCase().includes(t)?'':'none'}}
</script>"""


def _row(m) -> str:
    link = source_href(m)
    meta = " · ".join(
        str(x)
        for x in (
            f"#{m.id}",
            m.layer,
            "hidden" if m.hidden else None,
            f"score {m.walk_score}" if m.walk_score is not None else None,
            m.extraction_confidence,
            f"{m.happened_at} ({m.happened_precision})" if m.happened_at else None,
            ", ".join(m.tags or []),
        )
        if x
    )
    extra = {"links": m.links, "enrichment": m.enrichment}
    return f"""<details class="{"hidden" if m.hidden else ""}">
<summary><b>{escape(m.place)}</b> — {escape(m.summary[:120])} <span class=meta>{escape(meta)}</span></summary>
<div class=body>{escape(m.summary)}</div>
{f"<p><i>“{escape(m.quote)}”</i> — {escape(m.quote_by or '')}</p>" if m.quote else ""}
{f"<p class=meta>Then/now: {escape(m.contrast_note)}</p>" if m.contrast_note else ""}
<p class=meta>{escape(m.source_name or "")} · {escape(m.title or "")} · {escape(m.attribution or "")}
{f' · <a href="{escape(link)}" target=_blank>source</a>' if link else ""}
{f' · <a href="https://www.openstreetmap.org/?mlat={m.lat}&mlon={m.lng}#map=18/{m.lat}/{m.lng}" target=_blank>{m.lat:.5f}, {m.lng:.5f}</a>' if m.lat is not None else ""}
· created {m.created_at:%Y-%m-%d}</p>
<pre>{escape(json.dumps(extra, indent=2, ensure_ascii=False, default=str))}</pre>
</details>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/":
            self.send_error(404)
            return
        with get_session() as session:
            rows = session.execute(text(QUERY)).all()
        body = PAGE.format(count=len(rows), rows="\n".join(map(_row, rows))).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    print(f"http://127.0.0.1:{args.port}")
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
