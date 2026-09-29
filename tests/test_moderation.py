"""What people post is screened before a stranger can read it (App Store 1.2)."""

import pytest
from sqlalchemy import text

from api.moderation import refused
from tests.test_api_submit import submission


@pytest.mark.parametrize(
    "post",
    [
        "Ring me on +45 12 34 56 78",
        "call 12345678 after dark",
        "write to anna@example.com",
        "cheap rooms at www.example.com",
        "see https://example.com",
        "some nigger shouted at us",
    ],
)
def test_refused(post):
    assert refused(post)


@pytest.mark.parametrize(
    "post",
    [
        "The bar ran from 1978-1985, and it was fucking cold that night.",
        "Ringkaféen sank into the ground when the metro broke through.",
        "Tickets were 250 kr in 1996.",
        "Bus 5C stopped at Nørreport at 23.45.",
    ],
)
def test_passed(post):
    assert not refused(post)


@pytest.mark.db
def test_a_refused_post_is_never_stored(api_client, db_session):
    body = submission(summary="Call me on 12 34 56 78 if you were there.")
    assert api_client.post("/v1/memories", json=body).status_code == 422
    assert db_session.execute(text("SELECT COUNT(*) FROM memories")).scalar() == 0


@pytest.mark.db
def test_a_passed_post_is_stored(api_client):
    assert api_client.post("/v1/memories", json=submission()).status_code == 201
