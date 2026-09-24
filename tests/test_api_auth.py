"""Google and Apple sign-in: what a token has to survive, and what it buys.

No network and no real provider. A local RSA key stands in for the published
key set, which is the only way to test the checks that matter - a test that
mocks out verification proves the endpoint calls a function, and the endpoint
calling a function was never the risk.

The three checks are all failure-open if you get them wrong, and the middle one
is the one people actually forget: a valid Google token issued to *somebody
else's app* is still a valid Google token. Without an audience check, any app
whose users we can get a token from can sign in as ours.

The other half is the merge. Somebody files a memory, then signs in, and expects
it to come with them - and the same person on a second phone expects their
collection to be there. Neither is a nicety; the second one is the only reason
sign-in exists.
"""

import datetime
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import text

import api.auth as auth
from tests.conftest import on_todays_route
from tests.test_api_submit import LAT, LNG, device, submit

pytestmark = pytest.mark.db


@pytest.fixture
def client(api_client):
    return api_client


KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
GOOGLE_ID = "1234.apps.googleusercontent.com"
APPLE_ID = "com.example.memorylane"


@pytest.fixture(autouse=True)
def local_keys(monkeypatch):
    """Sign with our own key and let the real decode path run against it.

    Everything except where the key came from is genuine: algorithm, audience,
    issuer and expiry are all checked by PyJWT exactly as they are in production.
    """
    monkeypatch.setattr(auth, "signing_key", lambda jwks_url, token: KEY.public_key())
    monkeypatch.setattr(auth, "GOOGLE_CLIENT_IDS", [GOOGLE_ID])
    monkeypatch.setattr(auth, "APPLE_CLIENT_IDS", [APPLE_ID])


def token(**claims) -> str:
    now = datetime.datetime.now(datetime.UTC)
    body = {
        "iss": auth.GOOGLE_ISSUER,
        "aud": GOOGLE_ID,
        "sub": "google-user-1",
        "email": "someone@example.invalid",
        "email_verified": True,
        "name": "Lise",
        "iat": now,
        "exp": now + datetime.timedelta(hours=1),
    }
    body.update(claims)
    return jwt.encode(body, KEY, algorithm="RS256")


def apple_token(**claims) -> str:
    return token(
        **{
            "iss": auth.APPLE_ISSUER,
            "aud": APPLE_ID,
            "sub": "apple-user-1",
            "name": None,
            **claims,
        }
    )


def google(client, dev, **body):
    return client.post("/v1/auth/google", json={"device": dev, "id_token": token(), **body})


# -- what a token has to survive ----------------------------------------------


def test_a_real_token_signs_you_in(client):
    dev = device()
    profile = google(client, dev).json()
    assert profile["providers"] == ["google"]
    assert profile["user_id"] is not None
    # Google's name fills a blank, which is the only thing it is allowed to do.
    assert profile["display_name"] == "Lise"


def test_a_token_for_another_app_is_refused(client):
    """The check people forget. A valid Google token minted for somebody else's
    client id is still a perfectly valid Google token."""
    other = token(aud="9999.apps.googleusercontent.com")
    response = client.post("/v1/auth/google", json={"device": device(), "id_token": other})
    assert response.status_code == 401


def test_a_token_from_the_wrong_issuer_is_refused(client):
    stolen = token(iss="https://accounts.evil.invalid")
    assert (
        client.post("/v1/auth/google", json={"device": device(), "id_token": stolen}).status_code
        == 401
    )


def test_an_expired_token_is_refused(client):
    old = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=2)
    stale = token(iat=old, exp=old + datetime.timedelta(minutes=5))
    assert (
        client.post("/v1/auth/google", json={"device": device(), "id_token": stale}).status_code
        == 401
    )


def test_an_unsigned_token_is_refused(client):
    """alg=none is the oldest JWT hole there is and costs nothing to close."""
    unsigned = jwt.encode(
        {"iss": auth.GOOGLE_ISSUER, "aud": GOOGLE_ID, "sub": "x"}, key="", algorithm="none"
    )
    assert (
        client.post("/v1/auth/google", json={"device": device(), "id_token": unsigned}).status_code
        == 401
    )


def test_an_apple_token_is_not_a_google_one(client):
    """Same key, same shape, wrong issuer and audience for this endpoint."""
    assert (
        client.post(
            "/v1/auth/google", json={"device": device(), "id_token": apple_token()}
        ).status_code
        == 401
    )


def test_an_unconfigured_server_refuses_rather_than_accepts(client, monkeypatch):
    """With no client ids there is no audience to check against, and checking
    against nothing accepts everything. 503, because the caller did nothing
    wrong - this server cannot do sign-in."""
    monkeypatch.setattr(auth, "GOOGLE_CLIENT_IDS", [])
    assert google(client, device()).status_code == 503


def test_an_unverified_email_is_not_recorded(client, db_session):
    """Google hands one over for an account that never confirmed it, and a
    half-true address in our records is worse than none."""
    google(client, device(), id_token=token(email_verified=False))
    assert db_session.execute(text("SELECT email FROM identities")).scalar() is None


# -- what signing in buys ------------------------------------------------------


def test_the_same_account_on_a_second_phone_finds_its_collection(client):
    """The only reason this feature exists. Unlocks are recorded against a
    device; signed in, the collection has to follow the person."""
    first, second = device(), device()
    google(client, first)
    memory = submit(client, device=first)

    assert client.get(f"/v1/unlocks?device={second}").json()["memories"] == []
    google(client, second)

    carried = client.get(f"/v1/unlocks?device={second}").json()["memories"]
    assert [item["id"] for item in carried] == [memory["id"]]
    assert client.get(f"/v1/me?device={second}").json()["submitted"] == 1


def test_one_memory_earned_on_two_phones_appears_once(client, db_session):
    """Both devices have an unlocks row for it, and the collection is a list of
    things you have, not of times you got them."""
    first, second = device(), device()
    google(client, first)
    google(client, second)
    memory = submit(client, device=first)
    on_todays_route(db_session, second, memory["id"])
    client.post(
        f"/v1/memories/{memory['id']}/unlock", json={"device": second, "lat": LAT, "lng": LNG}
    )

    carried = client.get(f"/v1/unlocks?device={first}").json()["memories"]
    assert [item["id"] for item in carried] == [memory["id"]]


def test_what_you_filed_before_signing_in_comes_with_you(client):
    """Filing first and signing in later is the normal order, and losing the
    memory in between would be the version of this nobody forgives."""
    dev = device()
    memory = submit(client, device=dev, display_name="Bo")
    google(client, dev)

    profile = client.get(f"/v1/me?device={dev}").json()
    assert profile["submitted"] == 1
    assert profile["display_name"] == "Bo", "a chosen name outranks the provider's"
    assert client.get(f"/v1/unlocks?device={dev}").json()["memories"][0]["id"] == memory["id"]


def test_an_anonymous_user_is_absorbed_rather_than_left_behind(client, db_session):
    """Signing in on a phone that had already filed something, into an account
    that already exists elsewhere: the local anonymous user has to be folded in,
    not orphaned with the memory still attached to it."""
    first, second = device(), device()
    google(client, first)

    stray = submit(client, device=second)
    google(client, second)

    assert db_session.execute(text("SELECT COUNT(*) FROM users")).scalar() == 1
    assert client.get(f"/v1/me?device={first}").json()["submitted"] == 1
    assert client.get(f"/v1/unlocks?device={first}").json()["memories"][0]["id"] == stray["id"]


def test_two_real_accounts_are_never_merged(client, db_session):
    """A phone signed into one account, then into a different, existing one.

    Folding two accounts that each have their own sign-in together is a decision
    nobody here is in a position to make - so the device switches and both keep
    what is theirs. Only an *anonymous* user gets absorbed.
    """
    theirs, mine = device(), device()
    client.post("/v1/auth/apple", json={"device": theirs, "id_token": apple_token()})

    google(client, mine)
    submit(client, device=mine)
    assert client.get(f"/v1/me?device={mine}").json()["submitted"] == 1

    client.post("/v1/auth/apple", json={"device": mine, "id_token": apple_token()})

    assert db_session.execute(text("SELECT COUNT(*) FROM users")).scalar() == 2
    switched = client.get(f"/v1/me?device={mine}").json()
    assert switched["providers"] == ["apple"]
    assert switched["submitted"] == 0, "the Google account kept its memory"


def test_both_providers_can_be_attached_to_one_person(client):
    """Required in practice: iOS review insists on Apple once Google exists, so
    the same person will sign in with each of them at some point."""
    dev = device()
    google(client, dev)
    profile = client.post("/v1/auth/apple", json={"device": dev, "id_token": apple_token()}).json()
    assert profile["providers"] == ["google", "apple"]


def test_apple_carries_the_name_the_client_was_given(client):
    """Apple puts it nowhere in the token - it is handed to the app once, on the
    first authorization, and never again."""
    dev = device()
    profile = client.post(
        "/v1/auth/apple",
        json={"device": dev, "id_token": apple_token(), "display_name": "Ida"},
    ).json()
    assert profile["display_name"] == "Ida"


def test_signing_out_unlinks_without_deleting(client):
    dev = device()
    google(client, dev)
    memory = submit(client, device=dev)

    out = client.post("/v1/auth/signout", json={"device": dev}).json()
    assert out["providers"] == []
    assert out["user_id"] is None
    # Earned on this device, so still readable on it. The memory stays with the
    # account and comes back on the next sign-in.
    assert client.get(f"/v1/unlocks?device={dev}").json()["memories"][0]["id"] == memory["id"]
    assert client.get(f"/v1/me?device={dev}").json()["submitted"] == 0

    assert (
        client.post("/v1/auth/google", json={"device": dev, "id_token": token()}).json()[
            "submitted"
        ]
        == 1
    )


def test_signing_out_of_nothing_is_not_an_error(client):
    assert client.post("/v1/auth/signout", json={"device": str(uuid.uuid4())}).status_code == 200
