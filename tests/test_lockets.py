"""The locket a memory is drawn as: chosen by its author, any of them, and on
the pin before it opens. docs/10-decisions.md#lockets-one-per-memory-chosen-by-its-author-earned-by-level."""

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
        "celtic-knot",
        "moon-phase",
        "lovers-eye",
        "sweetheart",
        "quatre-couleur",
        "rose-egg",
        "dragonfly",
        "white-gold-frost",
        "etruscan-bulla",
        "mokume-river",
    }


def test_a_first_time_author_can_pick_any_locket(api_client):
    response = api_client.post("/v1/memories", json=submission(locket="victorian-garnet"))
    assert response.status_code == 201
    assert response.json()["locket"] == "victorian-garnet"


def test_a_round_four_locket_can_be_picked(api_client):
    response = api_client.post("/v1/memories", json=submission(locket="celtic-knot"))
    assert response.status_code == 201


def test_a_round_five_locket_can_be_picked(api_client):
    response = api_client.post("/v1/memories", json=submission(locket="mokume-river"))
    assert response.status_code == 201


def test_an_unknown_locket_is_refused(api_client):
    response = api_client.post("/v1/memories", json=submission(locket="tin-can"))
    assert response.status_code == 422


def test_an_edit_without_a_locket_keeps_it_and_one_with_a_locket_changes_it(api_client):
    dev = device()
    memory = submit(api_client, device=dev, locket="hunter-compass")
    edit = {"device": dev, "place_name": "Bench", "summary": memory["summary"], "media_ids": []}

    kept = api_client.put(f"/v1/memories/{memory['id']}", json=edit).json()
    assert kept["locket"] == "hunter-compass"

    changed = api_client.put(
        f"/v1/memories/{memory['id']}", json={**edit, "locket": "guilloche-oval"}
    ).json()
    assert changed["locket"] == "guilloche-oval"
