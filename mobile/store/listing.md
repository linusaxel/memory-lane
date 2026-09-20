# Store listing

Copy-paste ready. Character limits are asserted in `tests/test_store_copy.py`.

## Name (max 30)

Memory Lane

## Subtitle / short description (max 30)

Stories from where you stand

## Category

Travel (secondary: Entertainment)

## Description

Every place has a story. Memory Lane puts them on a map.

We listen to travel shows, comedy podcasts and video essays, pull out the moments
that happened somewhere specific, and pin them where they belong. Open the app and
you see the streets around you annotated with things that actually happened there —
the deli argument, the wrong turn that became the best night of the trip, the
restaurant that was somehow both terrible and unforgettable.

Tap any pin to read what happened. Tap again and the video opens at the exact
second the story is told, so you get it in the teller's own voice.

• A map of real stories near you
• Tap a pin for the place, the moment and the mood
• Jump straight to that second of the source video
• No account, no sign-up, no feed to scroll

Memory Lane is for the walk between places, the layover with an hour to kill, and
the neighbourhood you thought you already knew.

## Keywords (iOS, max 100 chars, comma separated)

travel,map,stories,nearby,places,podcast,city,guide,explore,local

## Support URL

https://github.com/linusaxel/memory-lane

## Privacy policy URL

https://<railway-domain>/privacy

(Served by the API itself — see `GET /privacy` in api/main.py. Replace the host
once W2-08 is deployed.)

## Screenshots required

- iOS: 6.9" (1320x2868). `supportsTablet: false` means no iPad set is needed.
- Android: at least 2 phone screenshots, plus a 1024x500 feature graphic.
  These need a real device — install the `preview` APK from EAS. Using the iOS
  screenshots on a Play listing is a policy risk.

Suggested three: the map with pins, a memory sheet open, the "Near me" view.

## Play Data safety answers

- Location (approximate and precise): collected, **not** stored, **not** linked
  to the user, used only for App functionality.
- No accounts, no personal identifiers, no advertising ID.
- Data is not shared with third parties.

## App Store privacy nutrition label

- Location → Precise Location → App Functionality → **Not** linked to the user.
- Nothing else collected.
