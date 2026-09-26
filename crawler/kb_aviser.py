"""Danish newspapers from KB Labs (Mediestream), searched by street name.

Free and keyless, but only papers over 140 years old (~pre-1886). The OCR is
rough Fraktur: `pwa` (predicted word accuracy) sits near 50 on every 1856 page
checked, so it filters nothing and is not asked for.
"""

import csv
import io
import urllib.parse
import urllib.request

URL = "https://labs.statsbiblioteket.dk/labsapi/api/aviser/export/fields"
FIELDS = ("link", "recordID", "timestamp", "familyId", "fulltext_org")

# ponytail: length is the only ad filter; a classifier if the hand count shows
# classified-ad pages cost more than the prompt already rejects.
MIN_CHARS = 200


class KbAviser:
    name = "kb-aviser"
    source_name = "KB Labs / Mediestream"
    source_type = "newspaper"

    def fetch(self, query: str, limit: int):
        params = [("query", query), ("max", limit), ("format", "CSV")]
        params += [("fields", f) for f in FIELDS]
        params += [("structure", "header"), ("structure", "content")]
        with urllib.request.urlopen(f"{URL}?{urllib.parse.urlencode(params)}", timeout=60) as r:
            rows = csv.DictReader(io.StringIO(r.read().decode("utf-8")))
            for row in rows:
                body = (row.get("fulltext_org") or "").strip()
                if len(body) < MIN_CHARS:
                    continue
                yield {
                    # `link` is the page and a page holds several articles:
                    # 13 of 200 rows shared one. The segment keeps each its own
                    # content.url; the fragment still opens the page.
                    "source_url": f"{row['link']}#{row['recordID'].rsplit('-', 1)[-1]}",
                    "title": f"{row['familyId']} {row['timestamp'][:10]}",
                    "text": body,
                    "language": "da",
                }
