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

**Numbers are stable.** F1–F7 are referenced from `mobile/UI.md`, `CLAUDE.md`,
`TODO.md` and from comments in the code, so they are not renumbered when new
flows are added, even where that leaves the order untidy. New flows get the next
free number. F3, F4 and F5 are still proposed and sit at the bottom.

---

## Index

| | | |
|---|---|---|
| F1 | Discover memories near me | Implemented |
| F2 | Read one memory and go to its source | Implemented |
| F6 | Many memories at one point | Implemented |
| F7 | Unlock a memory by standing near it | Implemented |
| F8 | Be asked for location | Implemented |
| F9 | Use the app without location | Implemented |
| F10 | Lose the network | Implemented |
| F11 | Find the nearest locked memory | Implemented |
| F12 | Walk there | Implemented |
| F13 | Walk into range | Implemented |
| F14 | Be refused an unlock | Implemented |
| F15 | Reread what you unlocked | Implemented |
| F16 | Read on the train home | Implemented |
| F17 | Understand why you cannot read something | Implemented |
| F18 | Stand somewhere with nothing in it | Implemented |
| F19 | Somewhere else entirely | Implemented |
| F3 | Arrive somewhere and find its history | Proposed |
| F4 | Switch between layers | Proposed |
| F5 | Contribute a memory | Proposed |

**Not flows, and deliberately absent:** there is no sign-in, no onboarding
carousel, no settings anybody has to change, no search in the app, no sharing,
and no notifications. Each of those is a thing a user does *not* do, and the
list is worth as much as the one above — if one of them appears, it should be
because a flow needed it, not because apps have them.

---

## The spine

Everything below is one of three sessions. If a flow does not belong to one of
these, it is probably not a flow.

**Session one — "what is this?"** Land on a map of padlocks (F1), get asked for
location in a way that explains the mechanic (F8), and either grant it and see
your reach drawn (F7) or decline and browse a city you are not in (F9). Nothing
is readable yet, and that is the pitch, not a failure.

**Session two — the first unlock.** Something is in reach, or the map tells you
how far the nearest one is (F11) and hands you walking directions (F12). You
arrive, the pin turns (F13), you hold the ring (F7), and a memory arrives (F7).
This is the entire product; every other flow exists to get somebody here or to
make it worth having got here.

**Session three — coming back.** The collection has things in it (F15), it works
on the train home with no signal (F16), and the map has memories you can already
read as well as ones you cannot. The You tab is where "why can't I read this"
gets answered before it becomes a complaint (F17).

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
Attestation needs accounts — Phase 3.

**"Forever" is a device promise.** Unlocks are recorded server-side, but against
an opaque UUID the app generates for itself and keeps in the keychain — there
are no accounts, so a new phone starts empty. Making it portable needs identity,
which is the same Phase 3.

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


## F8 · Be asked for location — **Implemented**

**Who:** somebody on their first launch, who has not been asked yet.

1. The map is already up and populated behind a card. Nothing has been asked.
2. The card says what the app does — *"Memories unlock where they happened"* —
   and what location is for, before the system dialog exists.
3. **"Turn on location"** hands over to iOS. **"Just show me the map"** dismisses
   it for good.
4. Granted → F7. Declined → F9.

The app never calls `requestForegroundPermissions` on mount. A cold system
dialog is one tap from a permanent no, and the reported gap is roughly 30%
opt-in against 65% after a primer — but the better reason is that "memories
unlock where they happened" is simultaneously the ask and the pitch, and there
is nowhere better to say it.

Somebody who already granted it is never asked again: `getForegroundPermissions`
runs first, silently. The dismissal is persisted, because re-asking every launch
is how an app teaches people to dismiss without reading.

**Failure:** already hard-denied (`canAskAgain === false`). The button becomes
**Open Settings**, which is the only route back.

**Done when:** a first launch shows a map with pins and no system dialog, and
the second launch of somebody who declined does not nag.

## F9 · Use the app without location — **Implemented**

**Who:** somebody who said no, or is indoors with location off.

1. The map stays on Manhattan, zoomed out, with pins.
2. Gated memories are all locked, and the sheet says so plainly rather than
   showing a distance it cannot know.
3. The bottom button reads **"Turn on location"** rather than "Near me", in
   every state.
4. No reach circle is drawn, because there is no reach.

This is a real mode, not an error. You can browse where the memories are,
read every centroid-placed one, and decide whether the app is worth granting
anything to. What you cannot do is open the gated ones, and the app says that
in words rather than showing pins that never respond.

**Done when:** nothing about this state looks broken, and nothing about it
pretends you can unlock.

## F10 · Lose the network — **Implemented**

1. A request that fails leaves **the last good pins on screen**. A map that
   empties itself on a dropped request looks like the area went blank rather
   than the connection.
2. The banner says "Can't reach Memory Lane" and the button becomes **Try again**.
3. Requests time out after 8s (`REQUEST_TIMEOUT_MS`). `fetch` has no default
   timeout, and a hung request rendering as "0 memories here" forever was the
   original bug.
4. Already-unlocked memories are unaffected — see F16.

**Failure within the failure:** a retry at the same viewport used to be skipped
by the fetch dedupe. Only *successful* fetches are recorded, so it is not.

## F11 · Find the nearest locked memory — **Implemented**

**Who:** somebody looking at padlocks, none of them in reach.

1. Where the "N within reach" pill would be, a muted one reads
   **"Nearest locked memory · 412 m"**.
2. Tapping it opens that memory's sheet, which offers F12.

It does not breathe and it is not seal red. "Walk 400 m" is information; only
something you can actually open is an invitation. A map of padlocks that answers
only "you cannot read this" and never "so where do I go" is half a mechanic.

## F12 · Walk there — **Implemented**

1. An out-of-reach memory's sheet shows the distance as a figure and a
   **"Walk there"** button.
2. It hands the coordinate to whatever maps app the phone has, with walking
   directions — Apple Maps on iOS, Google Maps elsewhere.

**Failure:** no maps app at all. `Linking.openURL` rejects and the sheet says
"No maps app to open directions in" rather than appearing to do nothing.

## F13 · Walk into range — **Implemented**

**Who:** somebody who took the directions.

1. Position is *watched*, not read once (`watchPositionAsync`, 25m). Walking
   into range changes the map by itself — a position read at launch would mean a
   pin only turns unlockable if you happen to press "Near me" while standing on
   it, which is the opposite of the mechanic.
2. The pin becomes a seal-red ring with a halo, and the reach circle now contains
   it.
3. The pill turns seal red, reads "1 memory within reach", and breathes.

**This is the moment the app is for**, and the reason nothing else on the map
moves.

**Done when:** walking 400m with the app open changes the map without any
interaction at all.

## F14 · Be refused an unlock — **Implemented**

**Who:** somebody who completed the hold and did not get a memory.

1. The ring fills, the heavier haptic fires, the request goes.
2. The server re-measures and says no, because GPS drifted between the press and
   the request.
3. The sheet says **"Not close enough yet — try a few steps nearer."**

The client decides which control to *show*; the server decides what may be
*read*, and those can disagree by a few metres. Silence here would read as a
broken button, which is the worst possible outcome for the one control the
product is about.

## F15 · Reread what you unlocked — **Implemented**

1. The **Unlocked** tab carries a count. It is the only number in the app that
   goes up because you went outside.
2. Newest first, as catalogue entries: place, the opening of the summary, when.
3. Tapping one opens the full sheet, which here carries **Show on map** —
   opened from a list, the place is a name, and this is the only route back to
   where it actually is. Over the map the button is absent, because there you
   are already looking at the answer.

Without this the reward for standing somewhere in the rain is one read, after
which the memory is buried under whichever pin you happened to be near and
findable only by going back.

**Edge:** memories unlocked before the app recorded timestamps have no date.
They sort last and simply do not say when, rather than reading "Invalid Date".

## F16 · Read on the train home — **Implemented**

The collection renders entirely from device storage. No network, no position, no
server. An unlocked memory is readable on the way home, in a tunnel, forever.

**The local copy is not the only copy any more.** An unlock is recorded against
this installation's UUID, so clearing the app's data no longer undoes the
walking. The local copy is what renders at launch and what works in a tunnel;
the server's arrives behind it and is merged in, with the local `unlocked_at`
winning because that is the moment the thing was actually earned.

**"Forever" is still a device promise.** There are no accounts, so a new phone
starts empty. Making it portable needs identity — Phase 3. This is written down
here because it is the kind of thing that is only discovered at the worst
moment.

## F17 · Understand why you cannot read something — **Implemented**

The **You** tab exists because every proximity-gated app needs somewhere to
answer that, and answering it only inside the sheet that provoked the question
is too late.

1. What this device has done: memories unlocked, places visited.
2. **How unlocking works** — the radius, that the *server* withholds the text,
   and that city-centroid memories are open to everyone because asking somebody
   to walk to a guess would be a lie.
3. Location state, with the route to Settings.
4. That nothing is synced and there is no account.

## F18 · Stand somewhere with nothing in it — **Implemented**

The banner reads "No memories here yet" and the map is otherwise normal. It no
longer looks like a failure, which was the bug. At street zoom the fetch is only
~700m, so this is easy to reach — panning two neighbourhoods over does it.

## F19 · Be somewhere else entirely — **Implemented**

**Who:** anybody not in New York, which is almost everybody. The corpus is one
comedy podcast's touring history.

1. The map comes up empty and stays empty however far you pan.
2. Instead of the banner alone, a card names the nearest place that is not
   empty: *"The closest memories are in New York. 64 of them, 6,189 km away.
   You still have to stand there to read one."*
3. **Show me New York** flies the map there, wide enough to take in the metro
   area rather than one pin.

Looking is not unlocking, and the card says so. You can see that the thing
exists; you still cannot read any of it from here. That distinction is the
product, and an empty-state card is exactly where it would be easiest to
accidentally abandon it.

**This outranks the location primer.** Asking for permission to unlock memories
that are not here is the wrong first impression, and "walk within 150 m of a
pin" is a promise about pins that do not exist. The primer gets its turn once
there is something on the map.

**Failure:** `/v1/stats` is unreachable, so there are no hotspots to name. The
card renders nothing at all and the banner is back to saying "No memories here
yet" — the same dead end as before, which is the right floor.

**Done when:** the app opened in Copenhagen explains itself instead of looking
broken.

---

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
