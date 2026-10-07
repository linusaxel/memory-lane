# Memory Lane redesign: implementation handoff

> Copied from the design export. The `screens/`, `html/`, `source/` and `assets/` it names stayed out of the repo (17 MB); ask the founder for the folder.

This folder is the design for Memory Lane's visual redesign, exported from the design canvas
(round 2). It is written for a coding agent working in the `memory-lane` repo. Read this file
first, then `docs/design-brief/README.md` in the repo for the product context.

## The decision

**Implement direction B, "Jewel Box"**, with two parts borrowed from A:

1. **Green "Go" buttons** (from A's moss): every start/next action is green enamel with a gold rim.
2. **A's stop checkboxes** on the walking card (done / next / later circles).

Direction A, "Field Journal", is included in full for reference only. Do not mix in anything else
from A unless the founder asks.

## What's in here

| Path | What it is |
|---|---|
| `screens/B-*.jpg` | **The visual truth.** One JPEG per screen, light mode on the left and dark on the right (2x). |
| `screens/A-*.jpg` | Direction A, for reference. |
| `screens/ICON-AddMemory.jpg` | 12 options for the Add-memory icon. The founder hasn't picked one yet; ship `v01-original` until he does. |
| `html/*.html` | The same screens as static HTML you can open in a browser and inspect for exact px values. |
| `source/*.dc.html` | The editable canvas source. The `renderVals()` in each file holds the exact light (`L`) and dark (`D`) token objects. |
| `assets/lockets/` | The pin locket (locked / opened), the big locket for the unlock view, and the six level lockets (`lk-*.svg`). |
| `assets/icons/` | The add-memory icon options, in four colourways each. |
| `assets/maps/` | Drawn stand-in maps. **Not for the app**: the real app uses Apple Maps. |
| `tokens.ts` | Proposed replacement for the colour/type part of `mobile/src/theme.ts`. |

The mockups are 390×844 phones with no status bar or keyboard drawn. Treat px as pt.

## Visual system (B)

- **Colour roles.** Each role means one thing:
  - gold = a memory and the way to it (links, route, pins);
  - green enamel = go;
  - gold foil = keep something (Seal it here, Subscribe, Done on the finish card);
  - emerald glow = openable now;
  - plum = what you earned (level bar, streak, your row on the board, XP).
  - Blue stays for the map and the user dot.
- **Paper.** Light is warm cream; dark is plum-black `#14101A`, replacing the brown.
- **Type:**
  - **Gloock** for titles, place names and big figures.
  - **Newsreader** for the story body and quotes. The story's first paragraph gets a Gloock drop cap in gold.
  - **SF Pro Rounded stays for all UI.** The mockups use Nunito only as a web stand-in; do not ship Nunito.
  - Load the two new fonts with `@expo-google-fonts/gloock` and `@expo-google-fonts/newsreader`.
- **Buttons:** 56–60 pt capsules.
  - **Go:** `goBg` fill, a 4 pt inset 1 px `goRim` ring, text in `onGo`.
  - **Foil:** a 3-stop vertical gradient (`#F6DE9A → #D9B45E → #B88E36`), a 1 px top highlight and an inset 1 px dark-gold ring; text `#1E1626`. Use `expo-linear-gradient`.
  - **Quiet:** `quiet` fill; in dark it gets a gold hairline.
  - **Text button:** gold.
  - Press squishes to 0.94.
  - Destructive actions are never gold: Delete account is muted red text, and End walk is quiet.
- **Ornament:** the diamond rule (line, emerald diamond with a gold edge, line) replaces the leaf-and-curls `Flourish.tsx`.
- **Quotes:** a centred pull quote: a large gold Gloock open-quote mark, Newsreader italic, and a small caption ("On the recording, at 11:23"). The gold left-bar callout goes.
- **Glass:** Liquid Glass stays over the map only, now with a gold hairline edge (`glassEdge`). Full sheets stay flat paper.
- **In reach:**
  - The locket hangs on its chain over a washed map, with a soft emerald glow behind it.
  - **There is no ring or outline around the locket.** The founder asked specifically to remove it.
  - Slide-to-open uses a green track and a foil thumb with a key icon.
- **Unlocking (B-18):** the lid swings open to show the engraved place name and coordinates. **The flash into the story is plum-black in dark mode, never white.** This fixes the current bug in frame 13f.
- **Walking card:** "Next · 280 m", the place name in Gloock, then four 16 pt stop circles and "3.2 km left". Done = gold fill with a check, next = gold ring, later = rule-coloured ring. A small ✕ ends the walk.

## Layout change: the bottom row on the map

Every map state uses one skeleton at the bottom:

| Position | Button |
|---|---|
| Bottom-left | **Add a memory** (60 pt glass circle, locket-with-plus icon) |
| Middle | The state's main thing |
| Bottom-right | **Center on me** (60 pt glass circle) |

- The middle slot is **Plan a walk** on the home map and **the walk card** while walking.
- In reach replaces the whole row with the slide track.
- The top row is unchanged: Journal on the left, Level pill in the middle, avatar on the right.
- Keep the Apple Maps attribution clear at bottom-left; the row sits above it.

## Screen map

| Board | Screen | Code (from the brief) |
|---|---|---|
| 01 | Splash with the redrawn app icon (locket whose chain is a winding lane, on a plum enamel tile) | native splash + `StartupLogo.tsx` + app icon assets |
| 02 | Sign in | `SignIn.tsx` (keep Apple's native button) |
| 03–06 | **New** onboarding, 4 steps | new `Onboarding.tsx`, shown once after first sign-in |
| 07 | **New** location primer before the OS prompt | new, inside onboarding |
| 08 | Home map | map stage in `App.tsx` |
| 09–10 | Planner steps 1 and 2 | `Plan.tsx` |
| 11 | Customize | `Plan.tsx` (subscriber step) |
| 12 | Pick where it ends | `Plan.tsx` |
| 13 | Walked out | planner |
| 14 | Walking | walk stage |
| 15 | End this walk? | walk stage |
| 16 | Locked peek | `MemorySheet.tsx` |
| 17–18 | In reach, unlocking | `UnlockHere.tsx`, `LocketUnlock.tsx`, `SlideToUnlock.tsx` |
| 19 | Finish card | walk stage |
| 20 | Past walk | from Your walks |
| 21–23 | Story: top, end with notes and Wikipedia, a person's memory | `StoryBody.tsx`, `Notes.tsx`, `WikiPreview.tsx` |
| 24 | Report | `MemorySheet.tsx` (the ⋯ menu stays a native action sheet) |
| 25–27 | Journal: walks / unlocked / mine (empty) | `Memories.tsx` |
| 28 | Your walks | `HowItWorks.tsx` |
| 29 | Board | board sheet |
| 30 | Account menu: **keep it native** (SwiftUI menu); only the row content changes | `AccountMenu.tsx` |
| 31 | Profile | edit profile sheet |
| 32 | Settings | settings sheet |
| 33 | **Custom paywall**: the six lockets on plum velvet | `Paywall.tsx` |
| 34–35 | File a memory, then "Seal it with" | `Submit.tsx` |
| 36 | Offline banner on the map | map stage |
| 37 | Crashed | `Crashed.tsx` |

## Constraints that still hold

These come from section 6 of the brief.

- Every text pair must be ≥ 4.5:1 in both modes. Update `tests/test_palette.py` with the new tokens and keep it passing.
  - The new `heart` (`#A3294E` / `#F29BB4`) and `danger` colours pass: 6.3 / 9.0 and 6.7 / 8.8.
- The map stays muted with POIs off; pins are the subject. There is one kind of pin, the locket: a keyhole when locked, plain when opened.
- **The dark map.** Apple Maps can't be recoloured, so to warm it toward the plum paper, try a translucent plum overlay view (about 10–15%) above the map and below the pins. Drop it if it hurts legibility.
- Android gets the light palette only.
- Native controls stay native: the account menu, action sheets, pageSheets and Apple's sign-in button.

## Don't take literally

- **Copy and data.** Some copy in the mocks is placeholder I invented: Maja's story, the grandmother quotes on Submit, the Christiansborg Wikipedia extract and the other names on the board. Use real data. Prices are `[PRICE]`; read them from the store.
- **The maps** are drawn stand-ins.
- **Stop positions** differ a little between screens.
- **Small layout slips.** A few boards have them, for example the Monthly price wrapping in B-33. Follow the intent, not the bug.
- **Onboarding copy** is a first draft that follows the copy rules. Run it past the founder.

## Suggested order

1. **Tokens and fonts.** Replace the colour and type values in `theme.ts` (see `tokens.ts`), load the fonts, and make `test_palette.py` pass.
2. **Buttons.** Build the Go, Foil, Quiet and Text button components and swap them in everywhere.
3. **Map chrome.** Do the bottom-row skeleton, glass edges and the walk card with the stop circles.
4. **The unlock.** Do in reach (glow, no ring), unlocking, and the dark-mode flash fix.
5. **The story.** Build the story sheet: Gloock and Newsreader, drop cap, diamond rule, pull quote.
6. **The sheets.** Do the journal, your walks, board, settings, profile and the paywall.
7. **Onboarding and location primer.** These are new screens.
8. **Submit and Seal.**
9. **App icon and splash.**

After each step, screenshot the simulator in light and dark (see "Retaking the screenshots" in the brief) and compare with the matching `screens/B-*.jpg`.
