# Store listing

Copy-paste ready. Character limits are asserted in `tests/test_store_copy.py`.

## Name (max 30)

Memory Lane

## Subtitle / short description (max 30)

A walk planner with memories

## Category

Travel (secondary: Entertainment)

## Description

Memory Lane is a walk planner with memories along the way. Each day it plans
a walk past real stories pinned to the places they happened, some from travel
shows and podcasts and some left by people who were there, and a story only
opens once you're standing on its spot. It's meant to make a familiar walk
feel new, because the ordinary corner you pass every day turns out to have a
story.

Pick how far you feel like going. Memory Lane plans a loop past about one
story a kilometre and lists what each is about. Not taken with them? Ask for
another walk. Then walk to each stop, hold to unlock, and read what happened
right where you're standing.

Most stories come with the moment they were told. Tap once and the video opens
at that exact second.

Leave your own, too. Stand where something happened to you, write it down, add
a photo or say it out loud, and it waits there for whoever walks by next.

• A new walk every day, as long or short as you like
• See what's on it before you go, or try another
• Stories unlock only on a walk, standing on the spot
• Jump to the second the story is told
• Leave your own, with a photo or a voice recording
• Finish a walk for a key, keep a streak, and reread anything you've unlocked

One walk a day is free. A subscription plans as many as you like.

## Keywords (iOS, max 100 chars, comma separated)

walk,walking,stories,history,nearby,places,podcast,city,guide,explore,local

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

## App Review notes

Sign-in comes first (F22), which Guideline 5.1.1(v) rejects unless the app has
real account features. Paste this into the review notes:

> An account is required because the collection is the product: every story
> you unlock is earned by walking to its spot, and your account is what carries
> that collection, and the memories you file, to a new phone. Sign in with
> Apple or Google; there is no password. To try the app, sign in, then press
> "Show me the walk". Location is optional; declining it plans a walk from
> central Copenhagen.

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
