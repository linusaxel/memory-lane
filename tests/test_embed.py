"""The embeddable map - the first surface with a customer attached.

Two things are worth guarding and the rest is markup.

The card must stay server-rendered. The reason the embed exists on somebody
else's page is also the reason the attribution cannot be assembled client-side:
this corpus is someone else's archive, and a customer's page must not be able to
drop the credit. So the frame points at the card route rather than building a
card from JSON.

And everything reaching the page must be bounded. It is a document we assemble
and serve to a third party's visitors, so an unvalidated parameter here is an
injection into their site, not ours.
"""

import json

import pytest
from fastapi.testclient import TestClient

import api.main as m
from api.embed import EMBED_HTML, EMBED_JS, TILE_ATTRIBUTION

client = TestClient(m.app)


def test_the_snippet_builds_an_iframe_not_an_injection():
    """An iframe keeps their CSS out of our map and our CSS out of their page,
    and gives their Content-Security-Policy a single origin to allow."""
    body = client.get("/embed.js").text
    assert "createElement('iframe')" in body
    assert "innerHTML" not in body


def test_the_snippet_resolves_the_frame_against_its_own_origin():
    """new URL(..., s.src) means a customer pastes one tag and nothing else -
    no base URL to configure and get wrong."""
    assert "new URL('/embed?' + q, s.src)" in EMBED_JS


def test_the_snippet_is_cacheable():
    assert "max-age" in client.get("/embed.js").headers["cache-control"]


def test_the_frame_asks_the_server_for_the_card():
    """If this ever becomes client-side rendering, the credit becomes optional."""
    assert "/card" in EMBED_HTML
    assert "'/v1/memories/' + m.id" in EMBED_HTML or "/v1/memories/' + id + '/card'" in EMBED_HTML


def test_the_map_credits_its_tiles():
    assert "openstreetmap.org/copyright" in TILE_ATTRIBUTION
    assert client.get("/embed").status_code == 200


def test_the_frame_defaults_to_copenhagen():
    """Density over coverage: the launch city is the default, not a world view."""
    body = client.get("/embed").text
    cfg = json.loads(body.split("var CFG = ")[1].split(";\n")[0])
    assert 55 < cfg["lat"] < 56
    assert 12 < cfg["lng"] < 13


@pytest.mark.parametrize(
    "query",
    [
        "lat=999",
        "lng=-500",
        "radius_km=0",
        "radius_km=10000",
        "zoom=99",
        "layer=public",
        "layer=<script>",
    ],
)
def test_an_out_of_range_parameter_is_refused(query):
    """This document is served to a customer's visitors. Everything in it is a
    bounded number or a pattern-matched enum, and nothing is interpolated raw."""
    assert client.get(f"/embed?{query}").status_code == 422


def test_config_reaches_the_page_as_json_not_as_string_interpolation():
    body = client.get("/embed?lat=55.6&lng=12.5&layer=friend").text
    cfg = json.loads(body.split("var CFG = ")[1].split(";\n")[0])
    assert cfg["layer"] == "friend"
    assert cfg["lat"] == 55.6


def test_an_empty_result_says_so_rather_than_looking_broken():
    """Pre-corpus Copenhagen returns zero memories. A blank map with no message
    reads as a bug, and it is the realistic case today."""
    assert "No memories recorded here yet" in EMBED_HTML
    assert "catch(function" in EMBED_HTML, "a failed fetch must reach the same message"
