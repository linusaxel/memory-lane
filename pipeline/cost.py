"""What a memory costs, from Anthropic's own bill.

    python -m pipeline.cost --since 2026-10-01 [--until 2026-10-05]

Spend is the Admin Cost Report API's, so web search, page reads and thinking
are in it, which the request logs miss. Memories are the ones extracted in the
same days. The bill is the organisation's: anything else on its keys counts
too. The target is at most $0.50 a memory (docs/04-extract.md, *Cost*).
"""

import argparse
import json
import urllib.parse
import urllib.request
from datetime import date, timedelta

from sqlalchemy import text

COST_REPORT = "https://api.anthropic.com/v1/organizations/cost_report"


def _fetch(url: str, key: str) -> dict:
    request = urllib.request.Request(
        url, headers={"x-api-key": key, "anthropic-version": "2023-06-01"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def spend(since: date, until: date, key: str, fetch=_fetch) -> float:
    """Dollars billed from `since` up to, not including, `until`."""
    params = {
        "starting_at": f"{since}T00:00:00Z",
        "ending_at": f"{until}T00:00:00Z",
        "limit": 31,
    }
    cents = 0.0
    while True:
        page = fetch(f"{COST_REPORT}?{urllib.parse.urlencode(params)}", key)
        cents += sum(float(r["amount"]) for b in page["data"] for r in b["results"])
        if not page.get("has_more"):
            return cents / 100
        params["page"] = page["next_page"]


MADE = """
    SELECT count(*) AS made, count(*) FILTER (WHERE NOT hidden) AS shown
    FROM memories
    WHERE user_id IS NULL AND created_at >= :since AND created_at < :until
"""


def main():
    from pipeline.config import ANTHROPIC_ADMIN_KEY
    from pipeline.db import get_session

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--since", type=date.fromisoformat, required=True)
    parser.add_argument("--until", type=date.fromisoformat, default=date.today() + timedelta(1))
    args = parser.parse_args()
    if not ANTHROPIC_ADMIN_KEY:
        raise SystemExit("ANTHROPIC_ADMIN_KEY is not set (Console, Settings, Admin keys)")
    dollars = spend(args.since, args.until, ANTHROPIC_ADMIN_KEY)
    with get_session() as session:
        r = session.execute(text(MADE), {"since": args.since, "until": args.until}).one()
    print(f"${dollars:.2f} for {r.made} memories ({r.shown} shown)")
    if r.made:
        print(f"${dollars / r.made:.3f} a memory, ${dollars / max(r.shown, 1):.3f} a shown one")


if __name__ == "__main__":
    main()
