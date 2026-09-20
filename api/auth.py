"""Google and Apple sign-in, and nothing else.

No passwords, so there is nothing to store, reset, rotate or leak, and no
password-reset email flow to build. Apple is not a preference either: App Store
review requires Sign in with Apple as soon as any other third-party sign-in
exists on iOS.

What arrives is an **ID token** - a JWT the provider signed - not an access
token. The app does the interactive part; the server's only job is to decide
whether the token is real and whose it is. That is three checks, and skipping
any one of them turns sign-in into "claim to be anybody":

  signature   RS256 against the provider's published keys, fetched and cached
              by PyJWKClient. Never `verify_signature=False`, never `alg=none`.
  audience    the token was minted for *our* app. A valid Google token issued
              to some other app is still a valid Google token, so an unset
              audience means any app's user can sign in as ours.
  issuer      Google's or Apple's, matched exactly.

Expiry is checked by PyJWT itself and is the reason not to hand-roll any of it.

There is no session token, and that is the point of the design rather than a
gap. The device id the app already sends is still the only credential; signing
in binds that device to a user, so every existing endpoint keeps working
unchanged and a second phone simply becomes a second device on the same user.
What sign-in buys is exactly that - a collection that survives a new phone - and
nothing else needed inventing to get it.
"""

import os

import jwt
from fastapi import HTTPException

# Comma-separated because an app has more than one. Google issues a separate
# client id per platform (iOS, Android, web) and a token is minted for whichever
# one asked; Apple's audience is the bundle id for the app and the Services ID
# for the web flow. Every id that may legitimately appear has to be listed, and
# nothing else may.
GOOGLE_CLIENT_IDS = [i for i in os.getenv("GOOGLE_CLIENT_IDS", "").split(",") if i.strip()]
APPLE_CLIENT_IDS = [i for i in os.getenv("APPLE_CLIENT_IDS", "").split(",") if i.strip()]

GOOGLE_ISSUER = "https://accounts.google.com"
GOOGLE_JWKS = "https://www.googleapis.com/oauth2/v3/certs"
APPLE_ISSUER = "https://appleid.apple.com"
APPLE_JWKS = "https://appleid.apple.com/auth/keys"

# Cached in-process: the key sets rotate on the order of days, and re-fetching
# per sign-in would put a network round trip in front of every one.
_clients: dict[str, jwt.PyJWKClient] = {}


def signing_key(jwks_url: str, token: str):
    """The provider's public key for this token. Patched in tests, which is the
    only way to exercise the audience and issuer checks without the network."""
    client = _clients.get(jwks_url)
    if client is None:
        client = _clients[jwks_url] = jwt.PyJWKClient(jwks_url, cache_keys=True)
    return client.get_signing_key_from_jwt(token).key


def verify(token: str, *, jwks_url: str, issuer: str, audiences: list[str]) -> dict:
    """Decode an ID token, or refuse.

    Every failure is the same 401 to the caller. Which check failed is useful to
    us and useful to somebody probing, and only one of those is worth serving.
    """
    if not audiences:
        # Not a 401: the caller did nothing wrong. Verifying against an empty
        # audience list would accept any app's token, so an unconfigured server
        # must say it cannot do this rather than do it badly.
        raise HTTPException(status_code=503, detail="Sign-in is not configured on this server")

    try:
        return jwt.decode(
            token,
            signing_key(jwks_url, token),
            algorithms=["RS256"],
            audience=audiences,
            issuer=issuer,
        )
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail="Sign-in token was not accepted") from e


def google_identity(token: str) -> tuple[str, str | None, str | None]:
    """(subject, email, name). `sub` is Google's stable per-account id.

    An unverified email is dropped rather than stored: Google will hand one over
    for an account that never confirmed it, and a half-true address in our
    records is worse than none.
    """
    claims = verify(token, jwks_url=GOOGLE_JWKS, issuer=GOOGLE_ISSUER, audiences=GOOGLE_CLIENT_IDS)
    email = claims.get("email") if claims.get("email_verified") else None
    return claims["sub"], email, claims.get("name")


def apple_identity(token: str) -> tuple[str, str | None]:
    """(subject, email). No name: Apple puts it nowhere in the token.

    It is handed to the app once, on the very first authorization, and never
    again - so the display name has to travel as a separate field from the
    client or be lost. `email` may be a private relay address, which is a real
    address and is treated as one.
    """
    claims = verify(token, jwks_url=APPLE_JWKS, issuer=APPLE_ISSUER, audiences=APPLE_CLIENT_IDS)
    email = claims.get("email") if claims.get("email_verified") in (True, "true", None) else None
    return claims["sub"], email
