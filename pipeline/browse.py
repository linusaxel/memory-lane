"""Every memory and all of it, on a map, for us. The page is browse.html.

Ungated on purpose, so it is a local tool and never a route on the API: it
reads the database directly and binds to 127.0.0.1 only. Hidden memories are
shown, faded. A pin is a place; the list beside the map is every memory, and
the filter box narrows both.

    python -m pipeline.browse            # http://127.0.0.1:8765
    python -m pipeline.browse --port 9000
"""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from sqlalchemy import text

from api.card import source_href
from pipeline.db import get_session

QUERY = """
SELECT m.id, m.summary, m.quote, m.quote_by, m.tags, m.layer, m.hidden,
       m.walk_score, m.extraction_confidence, m.happened_at, m.happened_precision,
       m.contrast_note, m.attribution, m.source_url, m.timestamp_start,
       m.links, m.enrichment, m.created_at, m.place_id, m.locket,
       p.name AS place, ST_Y(p.coordinates::geometry) AS lat, ST_X(p.coordinates::geometry) AS lng,
       p.precision_meters, p.geocode_status,
       c.title, c.source_name, c.url AS content_url, c.published_at,
       (SELECT count(*) FROM unlocks u WHERE u.memory_id = m.id) AS opens,
       (SELECT count(*) FROM memory_hearts h WHERE h.memory_id = m.id) AS hearts,
       (SELECT count(*) FROM reports r WHERE r.memory_id = m.id AND r.cleared_at IS NULL) AS reports,
       (SELECT json_agg(json_build_object('body', n.body, 'hidden', n.hidden) ORDER BY n.created_at)
          FROM memory_notes n WHERE n.memory_id = m.id) AS notes,
       (SELECT r.verdict || ' by ' || r.reviewer FROM memory_reviews r WHERE r.memory_id = m.id) AS review,
       (SELECT s.sheet FROM memory_sheets s WHERE s.memory_id = m.id ORDER BY s.id DESC LIMIT 1) AS sheet
FROM memories m
JOIN places p ON p.id = m.place_id
LEFT JOIN content c ON c.id = m.content_id
ORDER BY m.created_at DESC, m.id DESC
"""

PAGE = Path(__file__).with_name("browse.html")


def _memory(row) -> dict:
    return {**row._mapping, "link": source_href(row)}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0] != "/":
            self.send_error(404)
            return
        with get_session() as session:
            rows = session.execute(text(QUERY)).all()
        # "</" escaped so a summary can never close the <script> it sits in.
        data = json.dumps([_memory(r) for r in rows], default=str, ensure_ascii=False)
        body = PAGE.read_text().replace("__DATA__", data.replace("</", "<\\/")).encode()
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
