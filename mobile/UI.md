# UI guide

For agents working in `mobile/`. The app is two surfaces and one flow; this file
says what it looks like, why, and how to check you did not break it.

Read this before changing anything under `mobile/src/` or `App.tsx`.

## The app today

One screen, one modal.

```
MapView (full bleed)
├─ Marker per memory          tap -> MemorySheet
├─ banner  "N memories here"  top centre, non-interactive
└─ "Near me"                  bottom centre, recentres on GPS

MemorySheet (pageSheet modal)
├─ place name                 26/700
├─ distance · confidence      13/regular, green when high
├─ summary                    17/26 - the hero; there are no images
├─ tags                       pills
├─ source video title         italic, muted
└─ "Watch at 12:04"           red, deep-links YouTube at the second
```

## Tokens

These are already consistent across `App.tsx` and `MemorySheet.tsx`. Use them
rather than inventing new values — there is no theme file, so consistency is by
convention and reviewing eyes.

**Neutrals** (Tailwind zinc, by eye)

| Hex | Used for |
|-----|----------|
| `#18181b` | primary text, "Near me" background |
| `#27272a` | summary body text |
| `#3f3f46` | banner text, tag text |
| `#71717a` | secondary/meta text, Close |
| `#a1a1aa` | source attribution |
| `#d4d4d8` | sheet grabber |
| `#f4f4f5` | tag background, divider |
| `#fff` | sheet background, text on dark |

**Accents**

| Hex | Meaning |
|-----|---------|
| `#dc2626` | the watch action only. It reads as "video", and matches the map pins. Do not reuse it for generic emphasis. |
| `#15803d` | high confidence only |

**Type scale**: 26/700 (place), 17/26 (summary), 16/600 (primary button),
15 (close, button), 14/500 (banner), 13 (meta, source), 12 (tag).

**Radii**: 12 primary button · 20–24 floating pill · 12 tag · 3 grabber.

**Elevation**: every floating element carries both `shadow*` (iOS) and
`elevation` (Android). Set both or it looks flat on one platform.

## Rules that are load-bearing

Each of these exists because something broke or would have been rejected.

1. **Never show a blank grey map.** `FALLBACK_REGION` points at Manhattan when
   permission is denied, because store reviewers routinely tap Deny and an empty
   map is a rejection. Any new view needs the same treatment: an empty state
   that still shows something real.
2. **Location is foreground-only.** `ACCESS_BACKGROUND_LOCATION` is explicitly
   blocked in `app.json` and asserted by `tests/test_app_config.py`. Requesting
   background location will fail the suite and the store review.
3. **Debounce map-driven fetches** (currently 400ms). Panning fires
   `onRegionChangeComplete` continuously; without it you DoS your own API.
4. **The API is radius-only.** `regionToRadiusKm()` circumscribes the viewport
   and clamps to 0.1–100km; outside that the API returns 422. There is no bbox
   endpoint.
5. **A memory with no coordinates cannot be drawn.** The API filters those out;
   do not assume `coordinates` is always present on types that allow null.
6. **`timestamp_url` is already correct.** It points at the right second. Never
   rebuild a YouTube URL by hand.
7. **`onRequestClose` is required on every Modal**, or the Android back button
   does nothing.

## Copy

Sentence case. No exclamation marks. Count strings are singular/plural aware
("1 memory here"). Errors say what failed in plain words — "Could not reach
Memory Lane" — never an error code, never a stack trace. Store-facing copy in
`mobile/store/` has character limits enforced by `tests/test_store_copy.py`.

## Verifying a UI change

`./loop/verify.sh` covers types and the pure logic, not appearance:

```bash
cd mobile && npm run typecheck      # also run by the gate
```

To actually look at it — this works today, no physical device:

```bash
# 1. API with real data
docker compose up -d --build

# 2. dev server on the booted simulator
cd mobile && EXPO_PUBLIC_API_URL=http://localhost:8080 npx expo start --ios

# 3. pre-grant location, or the permission dialog covers the first screen
#    ("booted" is a literal simctl accepts - no need to look up a UUID)
xcrun simctl privacy booted grant location-always host.exp.Exponent
xcrun simctl location booted set 40.7484,-73.9857   # Manhattan: where the data is

# 4. screenshot it
xcrun simctl io booted screenshot /tmp/app.png
```

If the dialog still appears, terminate and relaunch — the grant applies at
launch: `xcrun simctl terminate booted host.exp.Exponent` then re-open the
`exp://` URL. Scripted taps are not available; `osascript` has no assistive
access here, so anything past the first screen needs a human hand.

**Use `localhost` for the simulator, a LAN IP only for a physical phone.** Expo
bakes `EXPO_PUBLIC_API_URL` in at dev-server start, so if you pass your LAN IP
and then change network, the app silently shows "0 memories here" with no error
— the map still works, it just cannot reach the API. Restart the dev server
rather than debugging the app. Likewise `exp://<stale-ip>:8081` hangs on
"Opening project"; `exp://localhost:8081` does not.

Only one dev server can hold port 8081, and `npx expo start` cannot prompt in a
non-interactive shell — it just prints "Skipping dev server". Kill the old one
first: `lsof -ti:8081 | xargs kill -9`.

Set the simulator location to Manhattan. The seeded corpus is a US comedy
podcast — from Copenhagen you will correctly see an empty map and think you
broke something.

Pure viewport maths goes in `src/region.ts` with a `node --test` case beside it;
the gate runs `mobile/src/*.test.ts`. Component behaviour is currently untested
and there is no RN test runner installed — do not add one without asking.

## States

The map has four, and they must stay visually distinct — the bug this replaced
was that "nothing here" and "we could not ask" rendered identically:

| State | Banner | Button |
|---|---|---|
| loading | "Finding memories…" + spinner | Near me |
| ready, n>0 | "N memories here" | Near me |
| ready, n=0 | "No memories here yet" | Near me |
| failed | "Can't reach Memory Lane" | Try again |

A failed refresh keeps the last good pins. Requests time out after
`REQUEST_TIMEOUT_MS` (8s) in `src/api.ts`; `fetch` has no default timeout and a
hung request is what produced the original bug.

## Markers

One marker is a *coordinate*, not a memory and not a place. 111 of 186 placed
memories sit on 34 coordinates, so a marker routinely stands for several
memories at several venues. A group of more than one carries a count badge, and
the sheet pages through it with "1 of 23 here".

Group in `src/cluster.ts`, never in the component — it is pure and unit-tested,
and the Times Square centroid is one of the test cases.

## The unlock control

The one place in this app allowed to be playful. Everything else is a quiet
map; this is the moment the product is *about*, so it gets the animation
budget. Spec, so it does not get re-invented per screen:

- **Press and hold, not tap.** ~900ms. A tap is a click; a hold is a lock
  turning. It also makes an accidental unlock almost impossible, which matters
  because unlocking is irreversible.
- **A ring fills around the button** over the hold, driven by
  `Animated.timing` with `useNativeDriver`. Releasing early springs it back —
  visibly, so the person understands they let go rather than that it failed.
- **Haptics carry the feel**: `ImpactFeedbackStyle.Light` on press-in, a
  `Medium` at completion. Never on release-cancel, which would read as a
  reward for failing.
- **Locked and unlockable look different on the map**, not just in the sheet.
  If you have to open a pin to learn you cannot read it, the map is not doing
  its job.
- **Never lock something already unlocked.** Re-locking punishes leaving.

Accessibility is not optional here, and a hold gesture is the easy thing to get
wrong: the control needs `accessibilityRole="button"`, a label that states the
gesture, and it must remain operable by a plain activation for anyone who cannot
hold. A gate nobody with a motor impairment can open is a gate on the wrong
people.

## Flows

Documented flows live in `docs/08-ux-flows.md`. Build toward those, and when a
flow changes, change that file in the same commit.
