"""The locket a memory is drawn as: chosen by its author, earned by level, and
on the pin before it opens. docs/10-decisions.md#lockets-one-per-memory-chosen-by-its-author-earned-by-level."""

import pytest

from tests.test_api_submit import device, submission, submit

pytestmark = pytest.mark.db


def test_a_memory_with_no_choice_draws_one_and_keeps_it_even_locked(api_client):
    memory = submit(api_client)

    locked = api_client.get(f"/v1/memories/{memory['id']}").json()
    assert locked["locked"] is True
    assert locked["locket"] == memory["locket"]
    assert locked["locket"] in {
        "hunter-compass",
        "guilloche-oval",
        "deco-sunburst",
        "monogram-cushion",
        "gold-line-night",
        "victorian-garnet",
    }


def test_a_level_one_author_cannot_pick_a_later_locket(api_client):
    response = api_client.post("/v1/memories", json=submission(locket="victorian-garnet"))
    assert response.status_code == 422


def test_an_unknown_locket_is_refused(api_client):
    response = api_client.post("/v1/memories", json=submission(locket="tin-can"))
    assert response.status_code == 422


def test_an_edit_without_a_locket_keeps_it_and_one_above_the_level_is_refused(api_client):
    dev = device()
    memory = submit(api_client, device=dev, locket="hunter-compass")
    edit = {"device": dev, "place_name": "Bench", "summary": memory["summary"], "media_ids": []}

    kept = api_client.put(f"/v1/memories/{memory['id']}", json=edit).json()
    assert kept["locket"] == "hunter-compass"

    refused = api_client.put(
        f"/v1/memories/{memory['id']}", json={**edit, "locket": "guilloche-oval"}
    )
    assert refused.status_code == 422
