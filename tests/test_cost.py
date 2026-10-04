"""Spend is summed over every page of the bill (pipeline/cost.py)."""

from datetime import date

from pipeline.cost import spend


def test_spend_sums_every_bucket_on_every_page():
    pages = {
        None: {
            "data": [{"results": [{"amount": "150.5"}, {"amount": "49.5"}]}],
            "has_more": True,
            "next_page": "p2",
        },
        "p2": {"data": [{"results": [{"amount": "100"}]}, {"results": []}], "has_more": False},
    }
    asked = []

    def fetch(url, key):
        asked.append(url)
        return pages["p2" if "page=p2" in url else None]

    assert spend(date(2026, 10, 1), date(2026, 10, 5), "k", fetch) == 3.0
    assert "starting_at=2026-10-01T00%3A00%3A00Z" in asked[0] and len(asked) == 2
