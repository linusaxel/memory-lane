# UX flows

What a person actually does, start to finish. One flow per section.

This file is the target, not a description of the code — where a flow is marked
**Proposed**, the app does not do it yet and the flow is the spec to build
toward. Implemented flows describe exactly what ships today; if you change
behaviour, change the flow in the same commit.

Visual conventions, tokens and the store-review constraints are in
[`mobile/UI.md`](../mobile/UI.md).

## Format

Each flow states: who, the trigger, the numbered path, what can go wrong, and
how you know it worked. Keep them concrete enough to test against.

**Numbers are stable.** F1–F7 are referenced from `mobile/UI.md`, `AGENTS.md`,
`TODO.md` and from comments in the code, so they are not renumbered when new
flows are added, even where that leaves the order untidy. New flows get the next
free number. F3 is still proposed and sits at the bottom.

---

## Index

| | | |
|---|---|---|
| F22 | Sign in | Implemented |
| F1 | Plan today's walk | Implemented |
| F2 | Read one memory and go to its source | Implemented |
| F6 | Many memories at one point | Implemented |
| F7 | Unlock a memory by standing near it | Implemented |
| F8 | Be asked for location | Implemented |
| F9 | Use the app without location | Implemented |
| F10 | Lose the network | Implemented |
| F11 | Find the nearest locked memory | Removed from the app |
| F12 | Walk there | Removed from the app |
| F13 | Walk into range | Implemented |
| F14 | Be refused an unlock | Implemented |
| F15 | Reread what you unlocked | Implemented |
| F16 | Read on the train home | Implemented |
| F17 | Understand why you cannot read something | Implemented |
| F18 | Stand somewhere with nothing in it | Removed from the app |
| F19 | Somewhere else entirely | Removed from the app |
| F5 | File a memory of your own | Implemented |
| F20 | Report something that should not be here, or block who wrote it | Implemented |
| F21 | Be somebody | Implemented |
| F23 | Seal a memory until a date | Removed from the app |
| F24 | Manage what you filed | Implemented |
| F3 | Arrive somewhere and find its history | Proposed |
| F4 | Switch between layers | Implemented |
| F25 | Walk today's route | Implemented |
| F26 | Heart a memory | Implemented |
| F27 | Keep a streak | Implemented |
| F28 | Get notified near a memory | Implemented |
| F29 | See what is locked around you | Implemented |
| F30 | Finish a walk | Implemented |
| F31 | Look back at a walk | Implemented |
| F33 | Leave a note | Implemented |
| F34 | End a walk | Implemented |
| F35 | Subscribe | Implemented (no store yet) |

**Not flows, and deliberately absent:** no onboarding beyond F22's one
screen — no carousel, no settings anybody
has to change (the walk length is the preview card's one slider, part of F1,
not a setting), no search in the app, no sharing, and no push notifications.
Each of those is a thing a user does *not* do, and the list is worth as much
as the one above — if one of them appears, it should be because a flow needed
it, not because apps have them. The one exception is F28's proximity
notification: local, opt-in, off by default, and the one thing in the app
that is allowed to interrupt somebody who is not looking at it.

---

## The spine

Everything below is one of three sessions. If a flow does not belong to one of
these, it is probably not a flow.

**Session one — "what is this?"** The map of what is locked around you (F29),
then **Plan a walk**: pick how far (F1), get asked for location by the button
that plans it (F8), see the walk on the map and accept it. Decline location and the walk is planned from central Copenhagen instead (F9). Nothing
is readable yet, and that is the pitch, not a failure.

**Session two — the first unlock.** The route pill says where the next stop is
(F25) and the line on the map is the way there. You arrive, the pin turns
(F13), you hold the ring (F7), and a memory arrives (F7).
This is the entire product; every other flow exists to get somebody here or to
make it worth having got here.

**Session three — coming back.** The collection has things in it (F15), it works
on the train home with no signal (F16), the streak says how many days in a row
(F27), and tomorrow there is another walk. The map shows what is locked around
you, never what it says: the walk is the only way in. The You sheet is where
"why can't I read this" gets answered before it becomes a complaint (F17).

---

## F22 · Sign in — **Implemented**

**Who:** everybody, on their first launch. The same screen again after signing
out, and on a new phone.
**Trigger:** opening the app with no account attached. It is the first flow,
because nothing is reachable before it (docs/10, *Sign-in comes first*).

1. The logo lands (StartupLogo) and the page grows around it: the name, one line
   ("The corner you pass every day has a story. Walk there to read it."), Apple's
   own control and Continue with Google. Nothing else — no carousel, no email
   field, no password, no magic link.
2. The provider's sheet, then back. The app sends the ID token it was given and
   is told who that makes it.
3. The map of what is locked around you (F29). Its **Plan a walk** draws a
   walk (F1), and that press is where location is asked for (F8).
4. On a new phone: sign in, and the collection is there.

Signing out (You → Account) lands back on this screen.

### Why it is the gate

The founder's call: no account, no app. The case for it, and what App Review
5.1.1(v) needs to hear, is the collection that follows you to a new phone. The
screen itself says only what the app is: the logo, the name, one line and two
buttons.

The last answer is kept on the phone, so a signed-in person on a train with no
network (F10, F16) opens straight to the map rather than a screen whose buttons
cannot work offline.

### Why only Google and Apple

No passwords means nothing to store, reset, rotate or leak, and no reset-email
flow to build. Apple is not a preference: App Store review requires Sign in with
Apple as soon as any other third-party sign-in exists on iOS. Both usually end
up on one account, which is why `identities` is a table and not two columns.

### What the server does with it

Verifies the signature, the **audience** and the issuer, then binds the device
to a user. No session token is issued in either direction — the device id it
already sends stays the only credential, so a second phone is simply a second
device on one person and every other endpoint is unchanged.

Signing out unlinks the device and deletes nothing. What was earned on the
handset stays readable on the handset; what was filed stays with the account and
comes back on the next sign-in.

**What can go wrong:** signing into an account that already exists, from a phone
that had already filed something before the gate existed — the anonymous local
user is folded in. Signing into a *different* real account switches the device
and merges nothing; two accounts that each have a sign-in are not ours to join
together. Cancelling the provider's sheet leaves the screen as it was, with no
message.

**Neither button works in Expo Go.** Apple needs the entitlement and Google
needs the app's own URL scheme, so a real sign-in needs a development build and
real client ids. A dev build shows **Skip (dev build)** under the buttons;
`__DEV__` strips it from a release bundle, and `./e2e/run.sh` taps it
(`.maestro/steps/sign-in.yml`).

**Done when:** a fresh install shows this screen and nothing behind it, and
somebody can hand their old phone in and still have everything they walked for.

---

## F1 · Plan today's walk — **Implemented**

**Who:** someone who opened the app and has not accepted a walk today.

1. **Plan a walk** on the map (F29), or **Walk here** on a pin's peek, draws a
   walk at once: no question first (docs/10, *Draw first, adjust after*). The
   press asks for location if it has to (F8), then `GET /v1/routes/preview`
   with that position, the length in metres, `loop` and the pin's `include`.
   The preview stores nothing.
2. The preview is the map, fitted to the start and every stop
   (`fitToCoordinates`), with the stops numbered and the loop drawn. Preview
   pins do not open: it is a look, not a walk. The card (`mobile/src/Plan.tsx`)
   reads "A walk from here", then "4 stops · 3.8 km loop", then the length:
   one slider, 1–10 km in 0.5 km steps, 4 km to start (`WALK_KM`), about one
   stop a km. Under it **Loop** or **One way**. No theme: tags are open since
   2026-09-26 (docs/10, *Tags come from the text*). One way adds **Pick where
   it ends**: the map, a card saying to tap it, and the tap is the end ("Ends
   where you tapped"; a second tap lets it go), with the slider at least the
   crow's distance to it ×1.3 (`endFloorKm`). Any change redraws the walk; the
   slider only on release. The × returns to the map.
   From **Walk here**, every walk passes that pin: the card reads "A walk
   through Blågårdsgade", and the length starts at the shortest walk that
   reaches it, twice the crow's distance (×1.3 on a loop, for the streets and
   the way back; `walkFloorKm` in `src/region.ts`). It has its own length:
   Plan a walk's is left alone. Show me another never drops the pin.
3. **Start walk** is `POST /v1/routes/today` with the same position, length and
   loop, and lands on the walk (F25).

**Accepting starts the walk.** It stands until it is ended (F34). Another the
same day needs a subscription, unless the first opened nothing (docs/10,
*A subscription opens the map*). A relaunch after accepting skips this
page and goes straight to the walk.

**What can go wrong:** nothing walkable within that length — the card moves the
slider up to the nearest length that has a walk and says "Nothing at 4 km; this
is the nearest." (F32). Nothing within 10 km at all reads "No walk within 10 km
from here." with the slider still there, and no Start walk. The map runs
out before the slider does (the lakes top out at 7.4 km) — a walk under 80% of
the ask (`ROUTE_FILL`) adds "That's the longest walk from here." No position
— the walk is planned from central Copenhagen and the card says so (F9). The server
unreachable — the card says "Can't reach Memory Lane right now." under the
button, and any change retries. From Walk here: the streets are longer than
the estimate, and the server's shortest length lifts the slider and the walk
is drawn again at it; further than 10 km reaches, "The nearest walk from
here is over 10 km." and no button; the pin can no longer be a stop (earned,
hidden), "That memory can't be on a walk from here." and the plan goes on
without it. Today's free walk already taken — "That was today's free walk.
Come back tomorrow, or subscribe for more." (the paywall comes with TODO.md S4).

**Done when:** Plan a walk shows a whole walk on the map, a change to the card
redraws it, and Accept makes it today's.

## F2 · Read one memory and go to its source — **Implemented**

**Who said this.** Every unlocked memory ends with the channel that published
it: avatar, name, episode title, tappable through to YouTube. Without it a
summary reads as the app's own assertion, and the app was not there.

It is also the answer to a question the summaries kept raising and never
answering. Over half of them open with *"the speaker"* — and one of them reads
"The speaker performed at **Joe List's** comedy showcase", where Joe List is one
of the two hosts. Nothing on screen said who anybody was. The channel says.

The extraction prompt now receives the same two facts, so it should stop needing
the label at all: see `source_context()` in `pipeline/extract.py`. Until a run
happens, the app carries the attribution the summaries lack.

**Who:** someone who sees a pin near a place they know.

1. Tap a pin → sheet slides up.
2. Place name, distance.
3. The summary is the point of the screen — a story about what happened there.
4. The source video title. A #word in the summary is a tag, set in the
   semibold; there are no tag pills.
5. "Watch at 12:04" → opens YouTube at that exact second.
6. Close, or Android back → returns to the map, viewport unchanged.

**Failure:** no YouTube app and no browser → `Linking.openURL` rejects, and the
sheet says so in place of the link rather than doing nothing.

**Done when:** the video opens at the right second and returning preserves the
map position.

---

## F6 · Many memories at one point — **Implemented**

Not an edge case. The extraction model emits a city centroid when it does not
know an address, so **121 of 215 placed memories sit on 28 shared coordinates** — one
point in Times Square carries 23 memories across 14 venues.

1. Memories are grouped by rounded coordinate (4dp, ~11m — tighter than the 50m
   the model calls "exact"), so repeated emissions of one centroid collapse and
   genuinely distinct addresses stay apart.
2. A group of one draws the normal pin. A group of more draws a count badge, so
   a stack is countable before it is tapped.
3. Tapping opens the sheet at the first memory with "1 of 23 here" and ‹ ›
   controls.

Grouped by coordinate, not by place id: one venue appears under several place
rows *and* several venues appear under one coordinate, so the coordinate is what
the eye sees and what the tap target should follow.

**This is mitigation, not a fix.** The underlying problem is that the
coordinates are wrong — see `docs/10-decisions.md`, "The coordinates are mostly
guesses". Clustering makes
23 stacked memories reachable; it does not put them at the right addresses.

---

## F7 · Unlock a memory by standing near it — **Implemented**

The core mechanic, not a feature. A memory you can read from your sofa is a
blog post; a memory you have to walk to is a reason to leave the house. This
is also what makes the card worth screenshotting — geo-gated content has no
other distribution channel (see *Core, not polish* in `docs/10-decisions.md`).

**Who:** someone looking at a map with pins they cannot read yet.

1. Every stop on today's walk draws a pin. A **locked** pin is a grey padlock and
   carries the place name and the distance — enough to decide whether to walk
   there — and nothing else.
2. The unlock radius is drawn around you, so "how much closer" is a distance you
   can see rather than a number to interpret. Walking inside it turns that pin
   into a seal-coloured ring, and the route pill says so in words: "Unlock
   memory", which opens the sheet.
3. The unlock is a deliberate physical act, not a tap: press and hold ~900ms
   while a ring fills, light haptic going in and a heavier one on completion.
   It should feel like a lock turning.
4. The memory reveals: summary, source, the watch link — animated once,
   because that arrival is the only payoff the product has.
5. It stays unlocked, and it stays in the journal under that day's walk (F15).
   Re-locking something they earned is a punishment for leaving.
6. The journal works with no network and no position: it renders from what the
   device stored, so a memory you walked to is readable on the train home.

**Only a stop of today's walk unlocks.** The server refuses anything else with
403, standing on it or not: five a day is the product, and the route it checks
against is its own `daily_routes` row, not anything the client says (docs/10,
"Only today's walk unlocks").

**Failure:** location permission denied. Nothing can unlock, so the app says so
— a bottom button reads "Turn on location", shown only then — rather than
showing a walk of permanently locked pins. The Copenhagen fallback is a planning
anchor and never an unlock position: where a walk starts and where the person
stands are two different parameters, precisely so that planning from a city
cannot open it.

**Failure:** the hold completes and the server still refuses, because GPS moved
in between. The sheet says "Not close enough yet", because a control that
appears to do nothing is the worse outcome.

**Failure:** location was never granted. The app never fires the system dialog
at mount — a cold dialog is one tap from a permanent no — and asks from the plan
page's button instead (F8). A hard refusal offers Settings.

**Done when:** standing at a place reveals its memory and standing a street away
does not. *Verified in the simulator:* memory 38 reads locked from the API and
open on the device across relaunches, which is the whole loop.

### The gate is server-side

The rule: *a client-side gate is not a gate*. If the API sends the summary and the client hides it, the
content is one `curl` away and the mechanic is theatre.

So a locked memory ships **place name, coordinates and distance, and nothing
else** — no summary, no tags, no source. The redaction lives in
`row_to_memory`, not in an endpoint, because gating `/v1/memories/nearby` alone
leaves side doors: `/v1/memories/search` reaches the same rows, and
`/v1/places/nearby` carries a verbatim summary as `sample_memory`.

The widest one was **`/v1/memories/{id}/card`**, and it stayed open after the
rest were closed. It renders a summary as HTML and does not go through
`row_to_memory`, so it had to be remembered separately and was not — and since
memory ids are sequential, one loop read the corpus. It is gated now: a gated
memory renders a **locked card**, which keeps the place name and the credit line
and replaces the summary with what to do about it. The credit survives because
attribution is the reason the card is server-rendered at all, and is no less
owed for a memory nobody has earned yet.

That shape is also what the embed wants. "There is a memory here, go and stand
in it" is a fine thing for somebody else's tourism page to say, and is now the
only thing it can say about a gated one.

Every one of these is asserted in `tests/test_api_unlock.py`. The lesson is
structural: any route that can emit a summary and does not route through
`row_to_memory` is a hole by default, so there should be as few of those as
possible.

**The list endpoints never unlock anything.** `/v1/memories/nearby` returns a
gated memory locked however close you are standing, and takes no position at
all. The single unlock is `GET /v1/memories/{id}?at_lat=&at_lng=`, which returns
the full memory only when that position is inside the radius and otherwise
reports the distance, so the app can say how much further to walk.

This was wrong the first time and worth stating plainly: if the map unlocks by
being stood on, the pin opens itself, there is nothing to press, and the
mechanic is a proximity query with extra steps. Walking into range *offers* the
unlock. The person performs it.

Reachability is therefore a client-side judgement — the app measures its own GPS
against the pin to decide which control to show — and that is fine, because the
server re-measures before it hands anything over.

The position is self-reported, so this stops `curl`, not a determined spoofer.
Attestation needs more than accounts, which now exist. See TODO.md.

**"Forever" means as long as the account does.** Unlocks are recorded
server-side against the keychain UUID, so clearing the app's data does not undo
the walking. Signed out, a new phone still starts empty; signed in, the
collection follows the person. That is F22, and it is the case for sign-in
coming first.

The client can still be generous with the animation. It just cannot be the
thing deciding what you are allowed to read.

### The radius fights the data

This is the part to decide before building, and it is unusual: **the
coordinates are wrong**. 121 of 215 placed memories sit on 28 shared centroids,
and the two Gotham Comedy Club rows are 2km apart while both claim 50m
precision.

Consequences, neither avoidable by tuning:

- A tight radius (50m) unlocks almost nothing. Standing at the real Gotham
  Comedy Club does not unlock the memory filed 2km away at Times Square.
- A loose radius (1km) unlocks 23 unrelated memories at once the moment you
  enter midtown, which is not a game, it is a dump.

`precision_meters` cannot rescue this either — 35 of the stacked centroid
places claim 50m.

**Decided: option 3 — only gate memories whose coordinates are trustworthy.**
A coordinate no other place shares is treated as real; a coordinate several
places share is the model saying "somewhere in this city", and locking that
would ask somebody to walk to a fiction. The other two options were: gate on
`precision_meters` once extraction tells the truth about it (correct in
principle, still blocked on a re-run), or one generous ~250m radius for
everything (ships, but dumps midtown in a clump).

Against the live corpus that gates **94 memories across 76 places** and leaves
121 centroid-stacked ones open — a locked set with real weight that shrinks the
moment the coordinates improve, with no behaviour to change when they do.

It also means the gated memories are, by construction, the *scattered* ones. No
round-number coordinate is near any of them, which is why the unlock cannot be
exercised from a Simulator without the dev seed in TODO 3.6.

The radius is **20m**: you stand at the place, not down the street from it.
Urban GPS can drift further than that between tall buildings, and that risk is
accepted (`docs/10-decisions.md#20-m`). `UNLOCK_RADIUS_METERS` in the API
environment if it turns out wrong in the street.

The app keeps the position live with `watchPositionAsync` (5m interval,
foreground only). Reading it once at launch means a pin turns unlockable only if
you happen to relaunch while standing on it, which is the opposite of the
mechanic.


## F8 · Be asked for location — **Implemented**

**Who:** somebody on their first launch, who has not been asked yet.

1. They have signed in (F22), looked at the map (F29, centred on central
   Copenhagen until there is a position). Nothing has been asked.
2. **Plan a walk** (or a pin's **Walk here**) is the ask: walks start from
   where you are. The system dialog comes from that press, never from launch.
3. Granted → the walk is planned from here. Declined → planned from central Copenhagen
   (F9).

The app never calls `requestForegroundPermissions` on mount. A cold system
dialog is one tap from a permanent no; a press with a reason in front of it is
not cold. There is no primer card any more — the press is the context.

Somebody who already granted it is never asked again: `getForegroundPermissions`
runs first, silently, and a granted launch starts watching position straight
away.

**Failure:** already hard-denied (`canAskAgain === false`). The press plans from
central Copenhagen without a dialog; on the walk, **Turn on location** opens Settings,
which is the only route back.

**Done when:** after F22, a first launch shows the map and no system
dialog, and Plan a walk or Walk here is the only thing that can raise one.

## F9 · Use the app without location — **Implemented**

**Who:** somebody who said no, or is indoors with location off.

1. The walk is planned from central Copenhagen (`FALLBACK_REGION`), and the preview says
   "Planning from central Copenhagen. Turn on location to plan from where you are."
2. Gated memories are all locked, and the sheet says so plainly rather than
   showing a distance it cannot know.
3. A bottom button reads **"Turn on location"**. It exists only in this mode.
4. No reach circle is drawn, because there is no reach.

This is a real mode, not an error, and never a dead end: a reviewer who taps
Deny still gets a walk on a real map (UI.md rule 1). What you cannot do is open
its stops, and the app says that in words.

**Done when:** nothing about this state looks broken, and nothing about it
pretends you can unlock.

## F10 · Lose the network — **Implemented**

1. Planning or accepting with no connection leaves you where you were, with
   "Can't reach Memory Lane right now." under the button. A second press
   retries.
2. An accepted walk renders from the local copy (`mobile/src/route.ts`) before
   the server answers, so a relaunch with no signal still shows it.
3. Requests time out after 8s (`REQUEST_TIMEOUT_MS`). `fetch` has no default
   timeout, and a hung request that never fails was the original bug.
4. Already-unlocked memories are unaffected — see F16.

## F11 · Find the nearest locked memory — **Removed from the app**

The "Nearest locked memory · 412 m" pill answered a map of padlocks. On a walk
the map shows only its stops, and the route pill (F25) names the next stop and
its distance.

## F12 · Walk there — **Removed from the app**

The sheet used to hand the coordinate to Apple or Google Maps. The walk is the
app's own: today's route is drawn on the map and the pill names the next stop,
so nothing sends you out of it.

## F13 · Walk into range — **Implemented**

**Who:** somebody following today's route.

1. Position is *watched*, not read once (`watchPositionAsync`, 5m). Walking
   into range changes the map by itself — a position read at launch would mean a
   pin only turns unlockable if you happen to relaunch while standing on it,
   which is the opposite of the mechanic.
2. The pin becomes a seal-coloured ring with a halo, and the reach circle now contains
   it.
3. The route pill turns seal-coloured and reads "Unlock memory" (F25).

**This is the moment the app is for**, and the reason nothing else on the map
moves.

**Done when:** walking 400m with the app open changes the map without any
interaction at all.

## F14 · Be refused an unlock — **Implemented**

**Who:** somebody who completed the hold and did not get a memory.

1. The ring fills, the heavier haptic fires, the request goes.
2. The server re-measures and says no, because GPS drifted between the press and
   the request.
3. The sheet says **"Not quite there. Take a few more steps."**

The client decides which control to *show*; the server decides what may be
*read*, and those can disagree by a few metres. Silence here would read as a
broken button, which is the worst possible outcome for the one control the
product is about.

## F15 · Reread what you unlocked — **Implemented**

1. **Journal**, top left of the map, opens the only other screen. The streak
   is on top, large (F27); under it *Walks*, *Unlocked Memories* and *My
   Memories* (F24).
2. *Walks* is this flow and F31: one row per walk, newest first. A row opens in
   place to its stops; an earned one opens the full sheet, one not walked to
   says so.
3. There is no **Show on map**: the map draws only today's walk, so a memory
   from another day has no pin to fly to.

*Unlocked Memories* is every unlock in one flat list, newest first, from the
device's copy (F16), each opening its sheet. What you filed yourself stays in
*My Memories*, not here.

## F16 · Read on the train home — **Implemented**

The journal renders from device storage first: the last walks list the server
gave (`route.ts` `loadWalked`) and the unlocked memories (`unlocked.ts`). No
network, no position. An unlocked memory is readable on the way home, in a
tunnel, forever.

**The local copy is not the only copy any more.** An unlock is recorded against
this installation's UUID, so clearing the app's data no longer undoes the
walking. The local copy is what renders at launch and what works in a tunnel;
the server's arrives behind it and is merged in, with the local `unlocked_at`
winning because that is the moment the thing was actually earned.

**Signed out, "forever" stops at this installation.** A new phone starts empty
unless the person has signed in — see F22. Written down here because it is the
kind of thing otherwise discovered at the worst moment.

## F17 · Understand why you cannot read something — **Implemented**

The journal's **You** section exists because every proximity-gated app needs somewhere to
answer that, and answering it only inside the sheet that provoked the question
is too late.

1. What this device has done: memories unlocked, places visited.
2. **How unlocking works** — the radius, that the *server* withholds the text,
   and that city-centroid memories are open to everyone because asking somebody
   to walk to a guess would be a lie.
3. Location state, with the route to Settings.
4. The name their submissions are signed with, and the sign-in that makes a
   collection survive a new phone, and signing out — see F22.

## F18 · Stand somewhere with nothing in it — **Removed from the app**

"No memories here yet" was the old nearby map's empty state. The map before a
walk (F29) just draws no pins, and Plan a walk leads to the preview's "No walk
that long from here" (F1).

## F19 · Be somewhere else entirely — **Removed from the app**

The hotspots card (`Elsewhere`, "Show me New York") pointed an empty map at the
corpus. With no browsing map there is nothing to point; from Copenhagen the
preview says "No walk within 10 km from here" (F1). `/v1/stats` still returns
hotspots for anyone who wants them.

---

## F5 · File a memory of your own — **Implemented**

**Who:** somebody standing somewhere something happened to them.
**Trigger:** the **Add** pin, top right of the map, at every stage: the
map, the preview, the walk, a walked day. Filing needs no walk.

1. The press checks for a position first. Without one it asks for location and
   stops — there is nothing to file *at*.
2. A full-height sheet opens. The first thing on it is not a field: it is the
   coordinate, and the sentence "other people will have to come here to read
   it".
3. **Title**, then **Description**. Post stays dim until both have text; no
   minimum length and no countdown, and the API asks for the same. The title
   is the place row's name (docs/10, *The title is the place name*), so it is
   the card's heading, locked or not; the description is what the gate keeps.
4. **When**: a date, today unless changed, from the platform's own picker.
5. **Tags** are the #words written in the description, as on X (`#food`):
   there is no picker, and the server reads them from the text.
6. **Photos** from the camera or the library, up to four, and one **recording**
   up to three minutes. Each one uploads the moment it is taken, so the wait is
   spent composing rather than watching a spinner after Post — and a failed
   upload costs the text nothing.
7. Post. The memory comes back already unlocked and its sheet opens on top of
   the map: the modal closing is not a confirmation, and this is also the first
   sight of what anybody else will find here.

### It files where you are, and nowhere else

There is no map picker, and that is not a missing feature. A memory you can pin
from your sofa is a pin; the entire product is the difference between those. One
coordinate goes to the server and it is both "where I am" and "where this goes",
so there is no pair of numbers that can disagree.

*ponytail: the position is self-reported, so this stops a casual post from the
sofa, not a determined one. Same ceiling as the unlock, and the same fix —
attestation needs real accounts.*

### It locks like everything else

A submission is gated the moment it exists, including for the person who wrote
it — so the unlock is recorded at insert time. Filing something *is* standing
there, and re-locking it the moment they walk away would be absurd.

The subtle half is the other direction. Each submission mints its own place row
at the submitter's GPS position, and F7's gate opens anything whose coordinate
another place shares. Without excluding submitted places from that count, filing
a memory outside Katz's would unlock Katz's for everybody — a gate anybody could
open by posting next to it. `tests/test_api_submit.py` holds it to that.

**What can go wrong:** no location (the form will not open); an upload fails
(the attachment shows as failed and Post waits rather than dropping it); the
post fails (the text stays on screen, nothing is lost).

**Done when:** somebody can stand somewhere, say what happened, and find it
waiting the next time they walk past — and so can a stranger who comes to the
same spot.

---

## F20 · Report something that should not be here, or block who wrote it — **Implemented**

Back on 2026-09-28 for App Store 1.2, which wants a report, a block and a filter.

**Who:** anybody who opened a memory somebody filed. Never on an extracted
memory (there is nobody to report a podcast to), never on your own.

1. Under the memory: **Report this memory**. One press, it reads "Reported",
   and nothing else changes for them. `REPORT_THRESHOLD` signed-in accounts
   hide it everywhere until `python -m api.moderate --restore` puts it back.
2. **Block {name}**, then a second press: "you will not see anything they post".
   The sheet closes and their pins leave the map, on every phone on the
   account. There is no unblock yet.
3. Posting something the screening refuses keeps the draft and says what can't
   be posted; a check that could not run is the ordinary "try again".

Settings → About → **Contact us** opens the policy at its Contact section.

---

## F21 · Be somebody — **Implemented**

**Who:** anybody who has filed something, or is about to.
**Trigger:** the You sheet (top right of the map). The submit sheet asks for no
name: a memory is signed by the account that filed it.

1. A name, saved as it is typed. No Save button to forget to press.
2. It appears under every memory they file, as "Left by —".
3. Blank is Anonymous, and clearing it has to keep working: the name is the one
   thing here other people see.
4. The You sheet gains a third figure once there is one — how many they have
   filed, beside how many they unlocked and in how many places.

A name needs no sign-in behind it. A `users` row is a display name and an id
that the device claims the way it already claims its unlocks - enough to sign a
submission, and not enough to identify anybody. Signing in (F22) attaches to the
same row rather than replacing it.

**What can go wrong:** signed out, the same person on a second phone is a second
stranger.
That is the gap sign-in closes and nothing else does.

**Done when:** a memory on the map has somebody's name under it and that name is
theirs to change.

---


## F23 · Seal a memory until a date — **Removed from the app**

Removed 2026-09-26: every memory is public. Anyone standing at a memory can
read it, and no memory can be held back until a date, not even by its author.
The "Who can read it" field is gone from the submit sheet, and the API no
longer accepts or returns `opens_at`. The `memories.opens_at` column is still
there, but nothing reads or writes it, so a memory sealed before the removal
is now ordinary. For the reasoning, see docs/10, *Every memory is public*.

---

## F24 · Manage what you filed — **Implemented**

**Who:** somebody who has filed at least one memory.
**Trigger:** the journal (F15) → *My Memories*. Empty until something is filed, and
it says so rather than hiding.

1. A list, newest first: place name and summary. A row reported by others carries a **Reported** badge instead of vanishing,
   because this is the one screen an author cannot have something disappear
   from without a reason.
2. Tapping a row opens the submit sheet in editor mode: every field prefilled
   from the memory, **Post** relabelled **Save**, and no map or coordinate
   field — the pin does not move.
3. **Save** changes place name, summary (and so its #tags), when, and photos/recording in
   place. **Delete** takes a second, differently-worded press before it
   commits — the same two-step this app uses in place of a system alert
   everywhere else — and removes the row, its media and its place outright,
   not the hidden flag a report uses.

**Always the server's list, never the local cache.** *Memories* has to show a
thing the offline unlock cache was never told about — one enough people
reported — so `/v1/me/memories` is asked fresh whenever
the journal opens or a save or delete lands, rather than reading `AsyncStorage`.

**What can go wrong:** the list fails to load (the sheet says so rather than
showing stale rows).

**Done when:** somebody can find every memory they have filed in one place,
fix a typo without re-filing, and take one down — and none of that touches
anyone else's collection or the local unlock cache.

---

## F25 · Walk today's route — **Implemented**

**Who:** somebody who accepted a walk (F1).
**Trigger:** Start walk on the preview, or any launch later the same day.

1. The accepted walk is up to five not-yet-earned memories, mixing historical
   and stranger layers and preferring higher-contrast ones, within the length
   chosen on the slider. Candidates come from within half that length of the
   start, because a loop cannot reach further. The server stores the choice and
   the length (`daily_routes.budget_meters`); every relaunch that day sees
   exactly this walk.
2. **The map shows the route and nothing else.** Its stops are the only pins;
   nothing off the route is fetched or drawn, and there is no reach banner and
   no hotspots card. Journal, You and Add sit in the top corners at every
   stage; there are no tabs. There is no
   "Near me": the pill recentres, and "Turn on location" shows only while
   there is no position.
3. **An ember glass bar at the top centre, "On a walk · 0 of 5"**, between
   Journal and You and Add, is what says this is a walk and not the map: it holds the
   count, and tapping it ends the walk (F34). Nothing else repeats the count.
   A pill at the bottom centre: "2.4 km to go" — the distance
   still to walk, from where you stand through every stop not yet earned, in
   order, and back to where the walk started on a loop (the preview's
   choice, stored as `daily_routes.loop`), so the walk home counts. Along the streets between stops
   when a routing server is running (`ROUTING_URL`), straight from you to the
   next stop, and said plainly as a distance, never as minutes. Tapping it starts the
   route and zooms out around you until the next stop is on screen (flies to
   the stop with no position, frames the whole route once it is walked);
   after that the pill reads "Next: <place> · 350 m".
   **The camera is pinned on you** while there is a position: it follows you,
   the map does not pan or rotate, and a pinch zooms without moving the
   centre. While the next stop is off screen, an ember arrow on the edge
   of the screen points the way to it.
4. Each stop draws the one pin (`mobile/UI.md`, "One pin") with its position
   (1–5) in the badge. There is no line while walking: the next unearned
   stop, in route order, hops and is `ember`, and when it is earned the
   one after it takes over. Only the preview draws the loop, washed-out ember under
   the street names (`mobile/src/RouteLine.tsx`, docs/09-visual-design.md
   §3a).
5. Reaching a stop lights its pin, and the pill turns seal and
   reads "Unlock memory"; a tap opens it. Any stop, in any order — the
   numbers suggest a walk, they do not enforce one. Unlocking is F7, unchanged.
   The badge and the hop drop away the moment it is earned, the
   numbers on the rest do not shift, and the pill's count and distance move.
6. The last stop earned, the bar reads "On a walk · 5 of 5", the pill
   reads "Every stop unlocked" and a tap fits
   the map to the whole walk. No confetti — the success haptic on that final
   unlock is the whole celebration.

**One walk at a time.** `POST /v1/routes/today` stores the first accept with
`ON CONFLICT DO NOTHING`; a second accept, from anywhere, at any length, gets
the first walk back until it is ended (F34). `GET /v1/routes/today` only reads
— 404 until something is accepted, or once it is ended — and is how a relaunch
decides between the walk and the map.

**Not a new mechanic — the same one, five times.** A route stop is nothing but
an ordinary gated memory with one extra fact attached, its position in today's
list. The unlock, the padlock and the sheet are F7's.

**Anchored on where the device was, not on a home it never gave.** The start is
the position sent with the preview and the accept, and nothing stores it — see
`docs/10-decisions.md` § Routes.

**No notification when it is ready, and none when it is finished.** F28 is the
one exception, opt-in, and it watches only this walk's stops.

**A sparse area gets an honestly shorter route, not a padded one.** Fewer than
five walkable memories within the length means a route of two or three, and
the card and the pill say so — "0 of 2" rather than pretending a fifth stop
exists. None at all is F1's "No walk within 10 km from here", and an empty walk is
never stored.

**Done when:** an accepted walk shows exactly its stops and nothing else,
survives a relaunch the same day unchanged, and the pill's count and the map's
badges track each unlock exactly as F7 already does.

---

## F26 · Heart a memory — **Implemented**

**Who:** someone reading a memory they have already unlocked.
**Trigger:** tapping the heart at the end of the sheet's credit line, beside "Left by".

1. The heart control only appears once a memory is open, never on a locked
   one - there is nothing to react to yet, and F7's gate has already decided
   who gets to see this far. No proximity check of its own: standing here
   again is not required, only having read it once already.
2. A tap records the heart server-side and fills the glyph. The count next to
   it - shown only once it is above zero - goes up by one.
3. It is one-way: tapping an already-hearted memory again is a harmless
   no-op, same count, same filled glyph. There is no way to un-heart.
4. The filled state survives a relaunch on this device (cached locally,
   `mobile/src/hearted.ts`), and the count survives everywhere - it is part
   of the memory itself, sent even while locked, the same as `media_count`
   and the anniversary flag.
5. Not your own. On a memory you filed the count shows, and there is nothing
   to tap; the API answers a heart on it with 403.

**Not a rating.** `docs/11-memory-types.md` rules out a star or a thumbs-up -
this is a count of "this mattered to someone," never a score, and it does not
change how anything sorts. Using it as a ranking signal is a later decision,
not this one.

**Failure:** the request fails (no network, server unreachable). Silent -
unlike F7's refusal, there is no gate outcome to explain, so the button
simply does not fill and nothing is lost by tapping it again later.

**Done when:** hearting an open memory fills the glyph and bumps the count
immediately, the state survives closing and reopening the sheet and
relaunching the app, and a locked memory shows no heart control at all.

**The author hears back.** Every row under Journal → My Memories says "3 hearts · 1
note", and a row whose count went up since the last look wears "New" (the tab
reads "Memories ·" until you open it). The baseline is on the phone
(`mobile/src/seen.ts`): no push, and the server stores nothing new.

---

## F27 · Keep a streak — **Implemented**

**Who:** someone who walks most days.
**Trigger:** none - it is the number on top of the journal, not a moment.

1. No counter is stored. `api.accounts.current_streak` reads the distinct
   calendar days this account (this device, or every device on the same
   account) unlocked **a stop of that day's walk** (`STREAK_DAYS_QUERY`, unlocks
   joined to `daily_routes`), and counts back from today for as long as the
   days are consecutive.
2. One stop is enough; the whole walk is not required. Filing does **not**
   count, though it records its own unlock (F5): otherwise a streak is kept by
   posting anything (decided 2026-09-24).
3. No stop yesterday *and* none today breaks it back to zero; none yet
   *today* does not, since the day is not over.
4. Shown large at the top of the journal (`Memories.tsx`), and on the closing
   card once it is more than one day (F30).

**Not a notification.** Nothing is pushed when a streak would break; it is a
truer number the next time the app is opened, same as F25's route pill. This
is the streak half of the founder-brainstorm's "streak + proximity
notification, reopened" resolution - F28 is the other half.

**Done when:** a walk stop on consecutive days increases the number, a skipped
day resets it, a day with only a filing does not count, and it reads zero for
a device that has never walked. `tests/test_streak.py`.

---

## F28 · Get notified near a memory — **Implemented**

**Who:** someone who turned on "Notify me when a memory is nearby" in
Settings.
**Trigger:** walking within a locked, walkable memory's unlock radius while
the app is not open.

1. **Off by default, and it asks for something the map never needs.**
   Turning the toggle on requests background location - `Location.
   requestBackgroundPermissionsAsync()` - which only runs if foreground
   permission is already granted, and notification permission. Turning it off
   just stops the watch; nothing else about the app changes.
2. The watch tracks today's accepted route (F25) - nothing before Start walk - a
   bounded, already-nearby list (`ROUTE_SIZE`, well under the ~20-region limit
   both platforms enforce for background geofences). `geofenceRegions.ts`
   drops anything already unlocked from the watch the moment
   the route list itself would.
3. Crossing into a watched region fires a **local** notification -
   `expo-notifications`, `trigger: null` - naming the place. No server push,
   no APNs/FCM registration: the background task (`expo-task-manager`) that
   detects the crossing runs entirely on the device.
4. A background task cannot read React state and can start from a killed app
   with nothing in memory, so the place name for each watched region is
   written to `AsyncStorage` alongside the geofence call and read back by the
   task using the region's identifier - not closed over.
5. Tapping it opens that memory's sheet, the same as tapping its pin. The
   memory id rides in the notification's `data`; `App.tsx` reads it with
   `useLastNotificationResponse`, which also covers a tap that launched the app.

**Opt-in on purpose.** This is the one feature in the app that asks for
location while the app is not open, and the only place `mobile/UI.md`'s "location
is foreground-only" rule bends - see rule 2 there for exactly what changed and
why the exception is scoped this narrowly.

**What can go wrong:** permission denied at either step (background location,
or notifications) leaves the toggle showing on with nothing actually watching
- `startWatching` returns `false` rather than throwing, so a denial is silent
the same way F26's heart failure is; there is no error state to show for a
feature that was never guaranteed in the first place. Background delivery
itself has not been verified end to end on a real device as of this commit -
see `mobile/UI.md` rule 2.

**Done when:** turning the toggle on with a route already loaded starts
watching that route's still-locked stops, turning it off stops the watch, and
`geofenceRegions.test.ts` holds the selection logic (locked, capped
at 20, nearest-radius-per-memory) to account without needing a device to
prove it.

---

## F29 · See what is locked around you — **Implemented**

**Who:** somebody signed in who has not accepted a walk today. Every launch
before an accept lands here; an accepted walk opens on the walk (F25).

1. The map, centred on you, or on central Copenhagen with no position. The
   pins are the locked memories within 5 km (`MAP_RADIUS_KM`, half the longest
   walk), from `/v1/memories/nearby`, fetched on arriving and again when a
   position first comes. Nothing open is drawn but what you filed: an open
   memory is not a reason to walk, and yours is where you left it. The map
   refetches when you file, edit or delete one. One you already earned wears
   its stamp.
2. Tap a pin: **the peek**, a card over the map rather than a page. Place,
   who it is from ("From" a source, "Left by" a person, with a glyph), its
   #tags, then the approach ring beside the distance with year · hearts and what
   is waiting, and **Walk here**, which draws a walk through that pin (F1).
   There is no unlock here, even standing on it: only today's walk unlocks.
3. **Plan a walk**, bottom centre, draws a walk (F1).

The peek is a look, not a read: the summary never reaches the phone locked, and
the peek draws nothing in its place. docs/10, "A locked memory says what it is,
not what it says".

Until 2026-09-26 this flow was removed: a map of every memory under the
viewport, where nothing opened, made the corpus a thing to browse and to
"complete". Locked pins cannot be read, so that rule survives: see docs/10, "A
map of what is locked, and only today's walk unlocks".

`App.tsx` (`stage === 'map'`, `fetchNearby`), `src/MemorySheet.tsx` (`onWalkHere`).

## F30 · Finish a walk — **Implemented**

The last stop unlocks and the day should feel finished.

1. The hold on the last stop opens its memory, with the success haptic twice.
   That memory is read first; nothing covers it.
2. Closing its sheet shows the closing card. The camera stops following you,
   and the map fits the whole walk, drawn from the start and back home on a
   loop.
3. The card reads "Nice walk.", then "5 memories · 4.1 km loop · 52 min" (the
   time is first unlock to last, and is left off if a stop was earned on
   another day), then the streak once it is more than one day (F27).
4. Done goes back to the map, pinned on you again, with the pill at
   "Every stop unlocked" under the bar's "On a walk · 5 of 5".

It shows once per walk, and nothing stores that it did: it follows the unlock
that finished the walk in this session, so a relaunch on a walked day lands on
the pill, not the card. There is no share button, by decision (2026-09-24).
`App.tsx` (`walkDone`), `src/Plan.tsx` (`WalkDone`), `.maestro/walk-and-unlock.yml`.
Why each of these, in `docs/10-decisions.md`, "The walk ends on a card, once".

## F34 · End a walk — **Implemented**

**Who:** somebody on a walk who wants out of it: a bad plan, rain, or a walk
already walked and another in mind.

1. The walk's bar, "On a walk · 2 of 5", top centre between Journal and
   You and Add (F25).
2. With stops still to reach, a card asks: "End this walk?", "The 3 stops you
   haven't reached will lock again. Anything you've unlocked stays unlocked.", **End walk** and
   **Keep walking**. A walked walk skips the card: nothing is lost.
3. Ended, the map of what is locked comes back (F29) with **Plan a walk**, and
   another walk can be planned the same day.

The ended walk stays in the journal (F31) with what it earned, and still counts
for the streak (F27). A walk that earned nothing is deleted as it ends. Its unearned stops cannot be unlocked any more (F14).
Offline, the card says "Can't reach Memory Lane right now." and the walk goes on.

`App.tsx` (`endWalk`, `confirmEnd`), `src/Plan.tsx` (`EndWalk`),
`POST /v1/routes/today/end`, `.maestro/walk-and-unlock.yml`. Why, in
`docs/10-decisions.md`, "A walk can be ended, and another planned".

## F31 · Look back at a walk — **Implemented**

Every walk that opened something is kept (`daily_routes`), and this reads
them back. One that opened nothing is deleted when it ends, or when the next
walk is accepted (docs/10, "A walk that opened nothing is deleted").

1. The journal's *Walks* section (F15): one row per walk, newest first,
   "Thu, Sep 24", its stops, "5 memories · 4.0 km": what it opened, never
   "3 of 5". Every walk listed opened something; what it missed is not the point.
2. A row opens in place to the memories it earned, numbered on a rail in
   walking order, each opening its sheet. Stops not reached stay out. Nothing
   is drawn on the map and nothing unlocks.
3. Across every device on a signed-in account (F22), and cached for the train
   (F16).

The km is the budget asked for, not metres walked, and the loop draws stop to
stop, not out and home: the start is never stored (docs/10 § Routes).
`GET /v1/routes/walked`, `src/Memories.tsx`,
`.maestro/walk-and-unlock.yml`, and `.maestro/lakes-loop.yml` on a seeded history.

## F32 · Show me another — **Implemented**

**Who:** somebody on the preview (F1) who wants a different walk of the same
length. **Trigger:** "Show me another", under Start walk.

1. The preview is replanned with `again` one higher, from the same length,
   loop. A different walk comes back whenever there is another as
   good: within a tenth of the slider of the best one on metres short of it
   plus metres retraced, and retracing no more (`ROUTE_VARIETY`,
   `api/route_solver.py` `_plan_route`). Taps cycle through those.
2. When it comes back unchanged, that was the only one at that length, so the
   card offers one of a similar length instead: the nearest other length that
   has a different walk (−0.5, +0.5, −1, +1, −1.5, +1.5 km, within the slider
   and above the pin's floor), and the slider moves to it. Never "the only
   walk". Only when none of those differs does the button go, with no line in
   its place.
3. Every walk shown is kept until the next fresh plan. With more than one, a ‹
   (Previous walk) sits left of Show me another and "2 of 3" under them. ‹
   steps back; Show me another first steps on through the walks ‹ passed, and
   only at the newest asks for another. Either way the slider moves to that
   walk's length, stepping needs no request, and VoiceOver hears "Walk 2 of 3".
   Not a swipe: nobody found it (the founder, 2026-09-29), and one forward
   button, not a › beside it, keeps the button that asks labelled.
4. Start walk sends the on-screen walk's `again`, so it stores the walk on
   screen. The client still never sends stop ids.

An empty length is the other dead end: a fresh plan with no stops moves up to
the nearest length that has a walk (10 km asked first, so nothing within reach
costs one request), and says "Nothing at 4 km; this is the nearest."

Every plan, and every change on the card, rolls a fresh `again`, so planning twice, or
tomorrow, can land on a different one of those walks without a tap. A walk already walked differs anyway: its
unlocked stops are no longer candidates. Without a routing server there is
nothing to judge a walk by, so each tap steps the length.

**Done when:** on the lakes seed a second tap previews a different loop, and
accepting it stores that loop. `tests/test_api_routes.py::test_another_day_*`.

## F33 · Leave a note — **Implemented**

**Who:** someone who has unlocked a memory, and its author. **Trigger:** the
note field under an open memory.

1. Notes sit under the summary of an open memory, oldest first, each signed
   with its writer's display name ("Anonymous" when blank, "You" for yours).
   A locked sheet shows only the count, beside the attachments: "2 notes
   waiting". The notes themselves are behind the gate: the server refuses the
   list to a device that has not unlocked the memory.
2. One note each, up to 280 characters, no replies. Posting again rewrites
   yours ("Rewrite"); it never adds a second.
3. "Remove" takes down your own note, and the author sees it on every note
   under a memory they filed. Hidden, not deleted.

**Why this and not comments:** see
[Notes are gated like a purchase](10-decisions.md#notes-are-gated-like-a-purchase).

**Failure:** the list fails to load: nothing shows, the memory still reads. A
note fails to send: "That didn't send. Try again.", the draft kept.

**Done when:** an unlocked memory takes a note and shows it back, a second note
replaces the first, the author can remove it, and a device that never unlocked
it gets 403 from both routes. `tests/test_api_notes.py`.

## F35 · Subscribe — **Implemented** (no store yet: TODO.md S6)

**Who:** somebody standing on a pin with no walk through it, or who has had
today's free walk. **Trigger:** **Open it now** on the map's peek, or a
second walk the same day.

1. On the map, a locked pin within reach says "You're right here. Make it a
   stop on today's walk, or open it now." with **Walk here** and, beside it, **Open
   it now**. Out of reach the peek is unchanged.
2. **Open it now**, a second walk the same day (`walked_today`), or an unlock
   refused `not_on_walk` opens the paywall (`src/Paywall.tsx`): "Open any
   memory you stand on", monthly and yearly at the store's price, **Restore
   purchases**, Terms and Privacy, and **Not now**.
3. A purchase or a restore asks the server to read the store back
   (`POST /v1/me/subscription`); only its answer opens anything. The sheet
   closes when it says subscribed.
4. A subscriber's peek, standing on the pin, is the ring: hold to open it, as
   on a walk. You shows "Subscribed until …" and **Manage subscription**;
   signed in and not subscribed, **Subscribe**.

**Why:** [A subscription opens the map](10-decisions.md#a-subscription-opens-the-map)
and [RevenueCat sells it; our table decides](10-decisions.md#revenuecat-sells-it-our-table-decides).

**Failure:** no RevenueCat key or no offerings (the simulator, e2e): "Subscriptions
aren't available right now." and **Not now**. The person backs out of the
store's sheet: nothing is said. Anything else: "That didn't go through. Try
again." A purchase the server cannot find: "No subscription on this
account yet."

**Done when:** `.maestro/subscribe-from-the-peek.yml` passes, and `tests/test_api_billing.py`.

## Proposed

Not built. Each needs a decision before it can be specified properly — see
*Open questions* at the bottom, and `TODO.md` for the phase each belongs to.

### F3 · Arrive somewhere and find its history — **Proposed** (Phase 1)

The core of the product brief: stand in a Copenhagen street, learn what
happened there. Blocked on choosing the historical source, and on deciding
whether it is a separate map layer, a filter, or a second pin style.

### F4 · Switch between historical, friend and stranger layers — **Answered: all at once, told apart in the sheet**

Not a segmented control and not a filter sheet. Layers are drawn at once, as
the same pin, and the sheet says which kind a memory is — a source to watch, or
the name of the person who stood there and wrote it.

Why no chooser: a filter is a control the map does not otherwise need, and
every overlay on this screen competes with the unlock. It also answers the
wrong question — nobody standing somewhere wants *fewer* of the memories that
are there.

Until 2026-09-23 the pin carried the layer by shape (round for `historical`, a
folded-corner card for `stranger`), since colour was already spoken for by
*openable*. It went in the one-pin simplification (`mobile/UI.md`, "One pin"):
shape plus five ink states plus a tag glyph was a legend to learn before the map
made sense, and a mixed stack could not honestly wear either shape anyway.

**The list half, added 2026-09-21.** The map drew every layer and
the feed underneath was still flat: `/v1/memories/nearby` ordered by contrast
alone, so a well-scored podcast anecdote sorted ahead of a note somebody left
standing at the same point. `LAYER_ORDER` in `api/queries.py` now leads the
ORDER BY — friend, then stranger, then historical — ahead of contrast, and the
sheet pager inherits it because the pager is the API's order.

Ahead of contrast rather than beside it, because *never at equal weight* is a
core rule and a tiebreak is equal weight with extra steps. Contrast still
decides everything within a layer, which is where it was always doing the work:
asserted both ways in `tests/test_api_nearby.py`.

`/v1/memories/search` is deliberately left on rank. Somebody who typed a word
asked for that word, and layer precedence there would answer a question nobody
put. One point is one feed; a search result set is not.


## Open questions

Answer these and the proposed flows can be written properly.

1. ~~**Layers: filter or stack?**~~ **Answered: stacked, with distinct pin
   shapes** — not colours, because the one accent is spoken for. See F4.
2. ~~**What does a person see with zero memories nearby?**~~ **Partly settled.**
   An empty length moves to the nearest one with a walk (F32); nothing within
   10 km says "No walk within 10 km from here" and offers the slider back (F1).
3. ~~**Is contribution in v1 at all**, or is v1 read-only?~~ **Answered: it is
   in.** F5 ships it, and the two things the old note said blocked it —
   moderation and an abuse story — turned out to be one report endpoint and a
   threshold rather than a project. Auth was the third, and it turned out not to
   be a blocker at all: a display name claimed by a device is enough to sign a
   memory. Real sign-in (Google and Apple, nothing else) followed, and since
   2026-09-26 it comes first (F22), for the collection rather than for
   contribution.
4. ~~**Does a pin represent a place or a memory?**~~ **Answered by
   implementation: a pin is a *point*.** Neither of the original options
   survived contact with the data — grouping by place id does not work, because
   one venue spans several place rows and several venues share one coordinate.
   A marker is now a coordinate, and the sheet pages through whatever is under
   it. If the coordinates are ever fixed, this can be revisited; while 60% of
   them are centroids, the point is the only honest unit.
5. ~~**Does the app sheet render the card, or duplicate it?**~~ **Answered: it
   duplicates it, and keeps doing so.** Three things the WebView version cannot
   do, none of which was obvious when the question was written:

   - **F16 works with no network.** Reading on the train home is a flow, and an
     iframe is a fetch. A collection that goes blank underground is not one.
   - **The unlock is the product and it is native.** The ring, the haptics, the
     stamp pressing down onto the page — F7 is animation on a `Animated.Value`,
     and a WebView is a rectangle you cannot reach into.
   - **The attribution argument has been met natively.** That was the only real
     case for the WebView, and the credit is now a pinned strip the story
     cannot scroll past (rule 11 in `mobile/UI.md`), with `tests/test_palette.py`
     holding the two renderings to one palette.

   The card keeps its three consumers where the client is *not* ours: the embed,
   a pasted link, and anything else that would otherwise drop the credit. That
   is what server-rendering it was for.
