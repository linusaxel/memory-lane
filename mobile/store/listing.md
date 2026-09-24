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

Most memories stay shut until you are standing near them. Walk within 150 metres
and you can open one — then it is yours to reread wherever you are.

Tap any pin to read what happened. Tap again and the video opens at the exact
second the story is told, so you get it in the teller's own voice.

And you can add your own. Stand somewhere something happened to you, write it
down, attach a photo or say it out loud, and leave it there for whoever comes
next.

• A map of real stories near you
• Unlock a memory by going to where it happened
• Jump straight to that second of the source video
• File your own, with a photo or a voice recording
• No password, no feed to scroll

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

Suggested three: the map with pins, a memory sheet open, today's walk from where you stand.

## Play Data safety answers

Answer these against `store/privacy.md`, not from memory — the app collects more
than it did before submissions and sign-in landed.

- **Location** (approximate and precise): collected, **not** stored, **not**
  linked to the user, App functionality. A coordinate you choose to attach to a
  memory you post is a different thing — see User content below.
- **Personal info → Name**: optional display name, collected and **stored**,
  **linked** to the user, shown publicly under what they post. App functionality.
- **Personal info → Email address**: collected only if you sign in with Google or
  Apple and allow it, stored, linked to the user, Account management. Not shown
  to anyone and never used to contact you.
- **Photos and videos**: collected only when attached to a memory, stored,
  linked to the user, **shown publicly**. App functionality.
- **Audio → Voice or sound recordings**: same as photos.
- **Messages / other user-generated content**: the memory text, its tags, the
  place name and the coordinates it was filed at. Stored, linked to the user,
  shown publicly.
- **App activity**: which memories an installation has unlocked, against a
  self-generated identifier.
- No advertising ID. Data is not shared with third parties and is not sold.
- Users can request deletion — see the Contact line in the privacy policy.

## App Store privacy nutrition label

- **Data linked to you**: Name (display name), Email address (sign-in only),
  Photos or Videos, Audio Data, User Content, Coordinates attached to a post.
  Purpose: App Functionality.
- **Data not linked to you**: Precise Location, used to find and unlock nearby
  memories. App Functionality.
- Not used for tracking. No third-party advertising.
