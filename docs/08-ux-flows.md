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

---

## F1 · Discover memories near me — **Implemented**

**Who:** someone who opened the app for the first time, standing somewhere.

1. App launches, map appears already centred on `FALLBACK_REGION` (Manhattan),
   zoomed out to ~10km — a preview of where the corpus is.
2. It primes for location rather than firing the system dialog (see F7).
   - **Granted** → animates to the person's position over 600ms and zooms in to
     street scale (~1.1km), with the unlock radius drawn around them. Fetches.
   - **Denied** → stays on Manhattan, still zoomed out, and fetches there. Never
     a blank map, and no circle, because nothing can unlock.
3. Pins drop for every memory with coordinates in the viewport radius.
4. Banner reads "N memories here".
5. Panning or zooming refetches, debounced 400ms, radius derived from the
   viewport and clamped to 0.1–100km.

**Three outcomes, three different things said.** They used to be two, and the
app could not tell you which one you were looking at:

| State | Banner | Button |
|---|---|---|
| loading, nothing yet | "Finding memories…" + spinner | Near me |
| ready, results | "N memories here" | Near me |
| ready, none | "No memories here yet" | Near me |
| failed | "Can't reach Memory Lane" | **Try again** |

A request that *hangs* used to be the bad case: `fetch` has no default timeout,
so an unreachable host sat on "0 memories here" with a spinner indefinitely and
the error path never fired. There is now an 8s timeout
(`REQUEST_TIMEOUT_MS` in `src/api.ts`).

A failed refresh keeps the last good pins on screen — they are still true of the
place, and a map that empties itself on a dropped request looks like the area
went blank rather than the network.

**Done when:** a pin appears within ~1s of the map settling, and the count
matches the pins drawn.

## F2 · Read one memory and go to its source — **Implemented**

**Who:** someone who sees a pin near a place they know.

1. Tap a pin → sheet slides up.
2. Place name, distance, confidence.
3. The summary is the point of the screen — a story about what happened there.
4. Tags; the source video title.
5. "Watch at 12:04" → opens YouTube at that exact second.
6. Close, or Android back → returns to the map, viewport unchanged.

**Failure:** no YouTube app and no browser → `Linking.openURL` rejects. Not
currently handled.

**Done when:** the video opens at the right second and returning preserves the
map position.

---

## F6 · Many memories at one point — **Implemented**

Not an edge case. The extraction model emits a city centroid when it does not
know an address, so **111 of 186 placed memories sit on 34 coordinates** — one
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
coordinates are wrong — see the centroid section in `TODO.md`. Clustering makes
23 stacked memories reachable; it does not put them at the right addresses.

---

## F7 · Unlock a memory by standing near it — **Implemented**

The core mechanic, not a feature. A memory you can read from your sofa is a
blog post; a memory you have to walk to is a reason to leave the house. This
is also what makes the card worth screenshotting — geo-gated content has no
other distribution channel (see *Design rules* in `TODO.md`).

**Who:** someone looking at a map with pins they cannot read yet.

1. Every memory in view draws a pin. A **locked** pin is a grey padlock and
   carries the place name and the distance — enough to decide whether to walk
   there — and nothing else.
2. The unlock radius is drawn around you, so "how much closer" is a distance you
   can see rather than a number to interpret. Walking inside it turns that pin
   into a seal-red ring, and the map says so in words: "1 memory within reach",
   which opens the sheet.
3. The unlock is a deliberate physical act, not a tap: press and hold ~900ms
   while a ring fills, light haptic going in and a heavier one on completion.
   It should feel like a lock turning.
4. The memory reveals: summary, tags, source, the watch link — animated once,
   because that arrival is the only payoff the product has.
5. It stays unlocked, and it joins the **Unlocked** tab. Re-locking something
   they earned is a punishment for leaving, and one read and then burial under
   a pin is barely better.
6. That tab works with no network and no position: it renders from what the
   device stored, so a memory you walked to is readable on the train home.

**Failure:** location permission denied. Nothing can unlock, so the app says so
— the bottom button reads "Turn on location" instead of "Near me" — rather than
showing a map of permanently locked pins. The Manhattan fallback is a *viewport*
and never an unlock position: the map centre and the person's position are two
different parameters, precisely so that panning to a city cannot open it.

**Failure:** the hold completes and the server still refuses, because GPS moved
in between. The sheet says "Not close enough yet", because a control that
appears to do nothing is the worse outcome.

**Failure:** location was never granted. The app primes rather than firing the
system dialog at mount — a cold dialog is one tap from a permanent no — and the
primer explains the mechanic, because "memories unlock where they happened" is
both the ask and the pitch. A hard refusal offers Settings.

**Done when:** standing at a place reveals its memory and standing a street away
does not. *Verified in the simulator:* memory 38 reads locked from the API and
open on the device across relaunches, which is the whole loop.

### The gate is server-side

`TODO.md` 3.3 already states the rule and it applies here: *a client-side gate
is not a gate*. If the API sends the summary and the client hides it, the
content is one `curl` away and the mechanic is theatre.

So a locked memory ships **place name, coordinates and distance, and nothing
else** — no summary, no tags, no source. The redaction lives in
`row_to_memory`, not in an endpoint, because gating `/v1/memories/nearby` alone
leaves two side doors: `/v1/memories/search` reaches the same rows, and
`/v1/places/nearby` carries a verbatim summary as `sample_memory`. Both are
gated, and `tests/test_api_unlock.py` asserts it.

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
Attestation needs accounts — Phase 3.

**"Forever" is a device promise.** The server does not know who unlocked what
and is not going to, so the collection lives in the app's storage. A new phone
starts empty. Making it portable needs identity, which is the same Phase 3.

The client can still be generous with the animation. It just cannot be the
thing deciding what you are allowed to read.

### The radius fights the data

This is the part to decide before building, and it is unusual: **the
coordinates are wrong**. 111 of 186 placed memories sit on 34 city centroids,
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

Against the live corpus that gates **83 memories across 74 places** and leaves
133 centroid-stacked ones open — a locked set with real weight that shrinks the
moment the coordinates improve, with no behaviour to change when they do.

The radius is **150m**, not the 50m the model calls exact. Urban GPS drifts tens
of metres, and a gate that will not open while you are standing on the spot is a
bug the person blames on themselves. `UNLOCK_RADIUS_METERS` in the API
environment if that turns out wrong in the street.

The app keeps the position live with `watchPositionAsync` (25m interval,
foreground only). Reading it once at launch means a pin turns unlockable only if
you happen to press "Near me" while standing on it, which is the opposite of the
mechanic.


## Proposed

Not built. Each needs a decision before it can be specified properly — see
*Open questions* at the bottom, and `TODO.md` for the phase each belongs to.

### F3 · Arrive somewhere and find its history — **Proposed** (Phase 1)

The core of the product brief: stand in a Copenhagen street, learn what
happened there. Blocked on choosing the historical source, and on deciding
whether it is a separate map layer, a filter, or a second pin style.

### F4 · Switch between historical, friend and stranger layers — **Proposed** (Phases 1, 3, 4)

Once memories carry a `layer`, the map needs a way to choose. Unanswered: is
this a segmented control, a filter sheet, or layers stacked at once with
different pin colours? At a dense location this decides whether the map is
readable.

### F5 · Contribute a memory — **Proposed** (Phases 3, 4)

Nothing in the app writes today; the API is read-only. Needs auth, moderation
and an abuse story before the UI matters.


## Open questions

Answer these and the proposed flows can be written properly.

1. **Layers: filter or stack?** One at a time, or several with distinct pin
   styles?
2. ~~**What does a person see with zero memories nearby?**~~ **Partly settled.**
   It says "No memories here yet" and no longer looks like a failure, which was
   the bug. Still open as a *product* question: should an empty area nudge the
   person to zoom out, or auto-widen the radius? Doing nothing is defensible
   until there is a corpus worth widening into.
3. **Is contribution in v1 at all**, or is v1 read-only?
4. ~~**Does a pin represent a place or a memory?**~~ **Answered by
   implementation: a pin is a *point*.** Neither of the original options
   survived contact with the data — grouping by place id does not work, because
   one venue spans several place rows and several venues share one coordinate.
   A marker is now a coordinate, and the sheet pages through whatever is under
   it. If the coordinates are ever fixed, this can be revisited; while 60% of
   them are centroids, the point is the only honest unit.
5. **Does the app sheet render the card, or duplicate it?** `GET
   /v1/memories/{id}/card` exists and is meant to have three consumers. The
   sheet is currently a native re-implementation of the same content. Using the
   card in a WebView would make attribution un-strippable in the app too, at the
   cost of native feel and offline rendering.
