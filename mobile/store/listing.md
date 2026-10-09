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

Answer these against `store/privacy.md`, not from memory.

- **Location → Precise**: collected, linked to the user, App functionality.
  The position is not stored in the database, but a walk's stops and street
  shape, each opened story with its time, and the request logs are.
- **Personal info → Name**: the display name (by default the name Google or
  Apple hands over), stored, linked, shown publicly under what they post. App
  functionality.
- **Personal info → Email address**: only if the provider hands over a verified
  one, stored, linked, Account management. Never shown, never used to contact.
- **Personal info → User IDs**: the provider's account id and our own; the
  self-generated installation identifier. Linked. App functionality, Account
  management.
- **Financial info → Purchase history**: whether a subscription is active and
  until when, via RevenueCat. Linked. App functionality.
- **Photos and videos**: attached to a memory or set as a profile photo,
  stored, linked, **shown publicly**. App functionality.
- **Audio → Voice or sound recordings**: same as photos.
- **Messages / other user-generated content**: the memory text, its tags, the
  place name and the coordinates it was filed at, and notes. Stored, linked,
  shown publicly.
- **App activity → App interactions**: walks, opened stories, hearts, reports,
  blocks. Linked. App functionality.
- No advertising ID, no tracking. Shared with processors only (Railway,
  RevenueCat, Anthropic), which Play does not count as sharing. Not sold.
- Data is encrypted in transit. Users can delete their account in the app.

## App Store privacy nutrition label

- **Data linked to you**: Precise Location, Name, Email Address, User ID,
  Purchase History, Photos or Videos, Audio Data, Other User Content, Product
  Interaction. Purpose: App Functionality.
- **Data not linked to you**: none.
- Not used for tracking. No third-party advertising.
- `ios.privacyManifests` in `mobile/app.json` declares the same list.
