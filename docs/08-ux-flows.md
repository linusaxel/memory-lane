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

1. App launches, map appears already centred on `FALLBACK_REGION` (Manhattan).
2. It immediately asks for foreground location.
   - **Granted** → animates to the person's position over 600ms, fetches.
   - **Denied** → stays on Manhattan and fetches there. Never a blank map.
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
