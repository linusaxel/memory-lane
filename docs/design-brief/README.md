# Memory Lane: design brief

A self-contained pack for a designer (or a design agent) asked to establish or
improve the app's visual style. It covers:

- what the app is;
- every view, with a screenshot;
- the visual system as built;
- what the founder has asked for, in their own words;
- what has been tried and thrown out;
- what a redesign must not break.

Captured 2026-10-06 on an iPhone 17 simulator (iOS 26.5), against the real
development corpus (Copenhagen, about 380 memories).

**Caveats on the screenshots:**

- The screenshots are 804×1748 JPEGs, scaled down from 3x.
- The Submit screen (31) was **mid-redesign** in the working tree when it was
  captured. It shows the bottom tool pill and the "Seal it with" step, which
  are not yet committed.
- "Bob / Safer" with the teal square is a junk test memory in the dev
  database, not real content.

Deeper references: [mobile/UI.md](../../mobile/UI.md) (tokens and load-bearing
rules), [docs/09-visual-design.md](../09-visual-design.md) (the reasoning
behind them), [docs/08-ux-flows.md](../08-ux-flows.md) (flows F1–F35),
[docs/10-decisions.md](../10-decisions.md) (why things are the way they are).

---

## 1. What Memory Lane is

> A walk planner with memories along the way. It's meant to make a familiar
> walk feel new, because the ordinary corner you pass every day turns out to
> have a story.

- The app plans **one free walk a day** past memories, about one per
  kilometre. A subscription buys more walks.
- Memories are short stories tied to an exact spot. Most are retold by AI from
  podcasts, papers, archives and Wikipedia ("Retold by AI from
  Københavnerglimt"). Some are filed by people ("Left by Maja").
- **A memory opens only on a walk, standing on its spot (within 20 m).**
  - There is no map browsing and no reading from the sofa.
  - The unlock is the moment the whole product builds towards.
- Every memory is public. Anyone standing there can read it.
- There is light progression:
  - XP per finished walk, and levels.
  - Six **lockets**, the pin designs, unlock with levels.
  - A streak, and a monthly city board.
- The bar for content is "**glad to know**". Accurate and tied to a place is
  only the floor. The founder's model memory is a 1980s pop duo filming a
  video on a specific rooftop.

## 2. Every view

The app has one map that never unmounts. Cards float over it by stage (home →
planner → walk), and everything else is a `pageSheet` modal. File references
are in `mobile/src/`.

### A. Before the map

| # | View | What it does | Screens |
|---|---|---|---|
| 01 | **Splash → animated logo** (`StartupLogo.tsx`) | The native splash shows the ember tile. Then the lane draws itself in and a sun drops onto it (~1 s). Skipped with Reduce Motion. | [splash](screens/01-splash-light.jpg) · [drawing](screens/01b-startup-logo-drawing-light.jpg) · [done](screens/01c-startup-logo-light.jpg) · dark: [splash](screens/01-splash-dark.jpg), [drawing](screens/01b-startup-logo-drawing-dark.jpg), [done](screens/01c-startup-logo-dark.jpg) |
| 02 | **Sign-in** (`SignIn.tsx`) | Logo tile, name, a one-line pitch, Continue with Apple / Google. Only Apple and Google, never email. "Skip (dev build)" is dev only. | [light](screens/02-sign-in-light.jpg) · [dark](screens/02-sign-in-dark.jpg) |
| — | Crashed (`Crashed.tsx`) | "Something broke." plus Try again. | *Not captured: needs a forced throw.* |

### B. The map and its cards

| # | View | What it does | Screens |
|---|---|---|---|
| 05 | **Home map** | Muted map, POIs off. Locked lockets nearby fade with distance. Top row: Journal (book), Level pill, avatar. Bottom row: gold **Plan a walk** (a tiny figure walks through the label on tap) and **+ Add a memory here**. Pins can't be tapped here. | [light](screens/05-home-light.jpg) · [dark](screens/05-home-dark.jpg) |
| 06 | **Planner, step 1** (`Plan.tsx`) | "A walk from here". The route draws itself over 1.2 s and each locket pops in when the line reaches it. ‹ › flips to another walk as good. Length slider 1–10 km; Loop / One way / Pick where it ends; Customize (Plus badge for free users, opens the paywall); Next. | [light](screens/06-planner-light.jpg) · [dark](screens/06-planner-dark.jpg) · [one way](screens/06b-planner-one-way-light.jpg) |
| 07 | **Planner, step 2: the stops** | A numbered list (place, source, #tags, a tiny locket) and **Start walk**. | [light](screens/07-planner-stops-light.jpg) · [dark](screens/07-planner-stops-dark.jpg) |
| 08 | Customize (subscribers) | Title and Clear; chips for 18 themes, richest first; one era of four; Done · N stops. | *Not captured: the screenshot account was a free one. See `docs/08-ux-flows.md` F1.* |
| 09 | **Walked out** | "Today's walk is done": there's another tomorrow, or subscribe. **More walks** opens the paywall. | [light](screens/09-walked-out-light.jpg) |
| 10 | **Pick where it ends** | "Where does it end? Tap the map where you want to finish." Cancel. | [light](screens/10-end-pick-light.jpg) |
| 11 | **Walking** | The route through the remaining stops, with the next pin highlighted. A glass card shows "Next: ‹place› · stamp dots · 3.2 km left" with ✕. Add on the left, Center on me on the right. | [light](screens/11-walk-light.jpg) · [dark](screens/11-walk-dark.jpg) |
| 12 | **End this walk?** | A confirm: unreached stops lock again, unlocked ones stay. End walk / Keep walking. | [light](screens/12-end-walk-confirm-light.jpg) |
| 13 | **In reach: the locket** (`UnlockHere.tsx`, `LocketUnlock.tsx`, `SlideToUnlock.tsx`) | The map washes out. A big gold locket hangs from the pin, with an iOS-style **slide to unlock** track below it (or hold 900 ms). The key turns, a "checking" tremble waits on the server, the lid swings open, sparkles appear, the place is engraved inside, then the view dives into the story. Haptics throughout. The founder calls this "the one place allowed to be playful". | [in reach](screens/13-in-reach-locket-light.jpg) · [key turning](screens/13b-unlock-key-turning-light.jpg) · [shine](screens/13c-unlock-shine-light.jpg) · [lid opening](screens/13d-unlock-lid-opening-light.jpg) · [open, engraved](screens/13e-unlock-open-engraved-light.jpg) · dark: [in reach](screens/13-in-reach-locket-dark.jpg), [shine](screens/13c-unlock-shine-dark.jpg), [open](screens/13e-unlock-open-engraved-dark.jpg), [dive flash](screens/13f-unlock-dive-flash-dark.jpg) |
| 14 | **Finish card** | "Nice walk." with the walk's shape, "4 memories · 3.4 km loop · 8 min", +XP, the level, a new locket if earned, the streak. Done; "Another walk today ›" for free users. | [light](screens/14-finish-card-light.jpg) |
| 15 | **A past walk** | Reopened from Your walks: the date, the old route on the map, Done. | [light](screens/15-past-walk-light.jpg) |

### C. A memory

| # | View | What it does | Screens |
|---|---|---|---|
| 16 | **Locked peek** (`MemorySheet.tsx`) | Tap a stop that's out of reach: place, source, #tags, an approach ring around the locket, the distance in big figures, "Get within 20 m to unlock it." | [light](screens/16-memory-locked-peek-light.jpg) · [dark](screens/16-memory-locked-peek-dark.jpg) |
| 18 | **The open story** (`StoryBody.tsx`) | Title, byline ("Retold by AI from ‹source› ↗" or "Left by ‹name›"), a leaf-and-curls flourish, the story (Wikipedia names underlined), a gold-barred **quote** callout ("at 11:23", the original words), a flourish, heart, notes. Opened right after an unlock, it rises in beats. | [light](screens/18-story-open-light.jpg) · [scrolled](screens/18b-story-open-scrolled-light.jpg) · [another](screens/18d-story-open-another-light.jpg) · [user-filed, short](screens/18c-story-user-filed-short-light.jpg) · dark: [top](screens/18-story-open-dark.jpg), [scrolled](screens/18b-story-open-scrolled-dark.jpg) |
| 19 | ⋯ menu | A native action sheet: Report this memory (and Edit / Block where they apply). | [light](screens/19-more-menu-light.jpg) |
| 20 | Report | An inline panel: "Why should it come down?" with four reasons. | [light](screens/20-report-light.jpg) (a stray keyboard is showing) |
| 21 | **Notes** (`Notes.tsx`) | Heart + count; "You were here. Leave a note." (280 chars). | [light, typed](screens/21-notes-light.jpg) |
| 22 | Wikipedia preview (`WikiPreview.tsx`) | Tap an underlined name and an inline callout appears: title, thumbnail, extract, "Read on Wikipedia ↗". | [light](screens/22-wiki-preview-light.jpg) (bottom half of the callout) |

### D. Sheets and menus

| # | View | What it does | Screens |
|---|---|---|---|
| 24 | **Account menu** (`AccountMenu.tsx`, a native SwiftUI menu) | Name; "1-day streak · 4 opened · 0 filed"; sign-in state; Edit profile; Board; Settings; Appearance (System/Light/Dark). | [light](screens/24-account-menu-light.jpg) · [dark](screens/24-account-menu-dark.jpg) |
| 25 | Edit profile | Avatar, Choose photo / Take photo, "Your name". Saves as you type. | [light](screens/25-edit-profile-light.jpg) |
| 26 | Board | "Copenhagen · Memories opened here this month." Ranked rows; you are in purple. | [light](screens/26-board-light.jpg) |
| 27 | Settings | Account (sign out, delete, subscribe), how unlocking works, location, nearby notifications, board opt-in, about. | [light](screens/27-settings-light.jpg) · [scrolled](screens/27b-settings-scrolled-light.jpg) · [dark](screens/27-settings-dark.jpg) |
| 28 | **Paywall** (`Paywall.tsx`) | "More than one walk a day", what you've done so far, the pitch, Yearly / Monthly, Restore, Not now. There is no store on the simulator, so it reads "Subscriptions aren't available right now" with the plan buttons missing. | [light](screens/28-paywall-light.jpg) · [dark](screens/28-paywall-dark.jpg) |
| 29 | **Your walks** (`HowItWorks.tsx`, opened from the Level pill) | Big "Level 2 · 80/200 XP", a shelf of walk shapes, locket counts by type, the opened lockets as a collection, then four short rule sections. | [light](screens/29-your-walks-light.jpg) · [scrolled](screens/29b-your-walks-scrolled-light.jpg) · [dark](screens/29-your-walks-dark.jpg) |
| 30 | **Journal** (`Memories.tsx`) | Header: avatar, name, counts. Tabs: Walks / Unlocked Memories / My Memories. A walk expands into its stops on a numbered rail. | [walks](screens/30-journal-walks-light.jpg) · [walk expanded](screens/30b-journal-walk-expanded-light.jpg) · [unlocked](screens/30c-journal-unlocked-light.jpg) · [mine, empty](screens/30d-journal-mine-empty-light.jpg) · dark: [expanded](screens/30b-journal-walk-expanded-dark.jpg), [unlocked](screens/30c-journal-unlocked-dark.jpg) |
| 31 | **File your own** (`Submit.tsx`, *mid-redesign*) | "Give it a name", byline (name · when ▾ · street), "What happened here?". The bottom pill holds Aa (B, I, A, quote, divider), photo and camera. Markdown-ish blocks: heading, divider (the flourish), quote, photos with caption, size and placement. Post leads to "Seal it with" ‹locket› → Seal it here. | [empty](screens/31-submit-empty-light.jpg) · [style bar](screens/31b-submit-style-toolbar-light.jpg) · [blocks](screens/31c-submit-blocks-light.jpg) · [photo](screens/31d-submit-photo-light.jpg) · [full draft](screens/31e-submit-photo-options-light.jpg) · [seal](screens/31g-submit-locket-seal-light.jpg) · [dark, empty](screens/31f-submit-draft-dark.jpg) |

**Not in the pack:**

- The OS permission prompts (location, photos, camera, microphone,
  notifications).
- The nearby-memory notification banner.
- Planning from the city centre when location is off.
- Error states ("Can't reach Memory Lane right now.").
- The Crashed screen.

## 3. The visual system as built

Source of truth: `mobile/src/theme.ts`. Rules: `mobile/UI.md`. Every colour is
a light/dark pair (`DynamicColorIOS`), and Android gets the light value.
`tests/test_palette.py` fails any text pair under 4.5:1.

**Ground** (light / dark):

| Token | Light | Dark | Note |
|---|---|---|---|
| paper | `#F7F4EE` | `#161412` | warm, chosen to sit close to the muted map |
| paperRaised | `#FFFDF9` | `#201D19` | |
| ink | `#1C1917` | `#F2EDE4` | |
| inkSoft | `#4A443D` | `#BDB5A8` | |
| inkFaint | `#746D65` | `#908979` | |
| rule | `#E0D9CC` | `#332E27` | |

**Three accents, one meaning each:**

- **gold** `#86661A` / `#D9B45E` = *a memory, and the way to it*. Used for
  the primary button, links, the next-stop tag and the route line. The line is
  washed out, `#E3CF98` / `#8A7238`, so the pins pop.
- **seal, emerald** `#1F6B4F` / `#3FA57E` = *openable now*, and nothing else:
  the halo on a pin in reach.
- **purple** `#5B2A6E` / `#C59BD8` = *what you earned*: the level pill bar,
  the streak, your row on the board.
- Blue belongs to the map and your location dot only.
- Locket metal ramp: `#FFF1C1 #F2D58A #D4AF5A #A8822E #6E5216`. Engrave
  `#8A6A22`, garnet `#8F1D1D`, night enamel `#211D18`.

**Type:** one family, SF Pro Rounded (`ui-rounded`), picked because it matches
the Apple Maps labels.

| Use | Size and weight |
|---|---|
| Story title | 28/34 |
| Story body | 17/26 |
| Label | 13, weight 600, sentence case |
| Display | 34 |
| Figures | 52 and 36 |
| Buttons | 17, weight 600 |

There is no uppercase and no mono. The web share card (`api/card.py`) still
uses Fraunces + Figtree.

**Shape and material:**

- Corners: field 14, card 28, pill 999.
- Buttons are flat 52 pt capsules in three styles:
  - solid gold;
  - quiet (an ink wash);
  - outline.
- Liquid Glass (`expo-glass-effect`) is used **only over the map**: untinted
  glass with a hairline edge, which squishes to 0.92 on press.
- Cards over the map are tinted glass. Full sheets (story, journal, settings,
  paywall) stay flat paper with hairlines. Never glass on glass.
- Two shadows only.

**Pins = lockets:**

- There is one kind of pin: the memory's gold locket, 32 pt. Its face shows a
  keyhole when locked and is plain when opened.
- Six designs, unlocked by level: Hunter compass (1), guilloché oval (3), deco
  sunburst (5), monogram cushion (7), gold line night (9), Victorian garnet
  (11).
- "In reach" = 1.35× plus an emerald halo.

**Motion:** the unlock sequence (section 2, row 13) and the route drawing
itself in the planner. During a walk, the next pin hops. Haptic success is
reserved for the open. There's no confetti: "the payoff is the words".

**Ornament:** a single leaf-and-curls flourish (`Flourish.tsx`), used under
the byline and before the notes. Callouts get a 3 px bar. Icons are SF
Symbols.

**Copy:**

- "Write like a friend pointing at a corner."
- No "we", no em dashes, no exclamation marks, no "hidden gem".
- Celebrations go in the words and the haptic ("Nice walk.").

**Brand:**

- The app icon and splash are still the **ember tile `#A8350F`** with a paper
  road and a sun, drawn before the gold palette. Redrawing them is an open
  item.
- The dark tile is a muddier brown.

## 4. The vibe, in the founder's own words

Dated quotes from the build sessions, grouped by theme.

**Overall feeling**

- 09-22: "app aesthetic; almost a **stardew valley esque vibe, cozy, warm and
  green tones** representing peace and walking through nature … add a "city"
  urban theme in the future"
- 09-22: "logo: a winding pathway, a gust of wind represented in a twirly way
  … on app startup, animated logo"
- 09-26: "the current stuff is **kinda AI-y**, i want it more polished and
  true to my vision and the intended simplicity/fun that this app is meant to
  be"
- 09-26: "there is some mismatch in colors, looks and button looks to sharp
  etc, **doesnt look fun or friendly**"
- 10-01: "how feasible is it to redesign the UI to have more of a **WoW kinda
  feel** - i'm thinking the quest UI, with that kinda font and paper ish
  texture"
- 10-01: "maybe we can take inspo from **assassins creed 2 "memories"**
  concept … for both the logo and the memory pins"
- 10-01: "**i'm not married to an aesthetic necessarily but just wanna make it
  fun/unique**"
- 10-03: "let's improve the look of the buttons … maybe we should revamp the
  UI as a whole. **feels a bit sterile** atm"
- 10-04: "we are shifting the aesthetic to a more **gold-oriented look with
  green/emerald/rich purple details**"
- 10-04: "can we make all interfaces **modern and glass looking and state of
  art** UI-wise?"
- 10-06: "i feel like i need to establish or improve the visual style of the
  app"

**Game feel and dopamine**

- 09-20: "the unlock button should be pretty and should be **fun to press,
  like a game almost**"
- 09-21: "add an actual unlock animation … which **rewards the user's dopamine
  system**"
- 09-29: "look into the **shazam button** and why it looks and feels so good,
  we need something similar for unlock memory"
- 10-01: "take inspiration from games, **i want this app to feel like a
  game**" … "**pokemon menu** maybe since we're "collecting" memories"
- 10-01: "let's ONLY have the lock icon/animation thingy and remove all and
  any text, just one big button"
- 10-02: "let's make this rpg-y and give users items … loot after every walk …
  am i getting ahead of myself"
- 10-04, later: "**too much gamification already**" (keys and an economy were
  dropped).

**Pins and lockets**

- 09-23: "this is too complicated. let's just have **a single kind of pin that
  is more beautiful looking**."
- 09-24: "make each pin that the user is next directed to **pop out, like
  bounce around a bit** and be brighter/more colorful"
- 09-26: "the black pins … **black is not an especially fun color**"
- 10-04: "these are **lockets** that will represent the memories … pins on the
  map … the unlock animation … users can customize which locket … leveling up
  unlocks more locket designs."
- 10-04: "is it feasible that the locket animation kinda **zooms into the
  memory content itself** … need a smooth transition there."

**Map and route**

- 09-24: "these lines are fucking FUGLY … looks at this screenshot of the
  **native apple maps app** - why cant we do something like that?"
- 09-27: "make the route line lighter so the pins pop"
- 10-03: "one smooth animation where the route draws itself and only when it
  reaches the memory does the memory pop in."

**Buttons, glass, contrast**

- 09-27: "actually lets ad the liquid glass thing fuck it"
- 09-27: "**all buttons should attempt to be consistent**, no?"
- 10-01: "i'd like to keep thing **symmetrical** and i like the highlight we
  use for the important buttons"
- 10-04: "plan a walk button, the color looks off and plain, maybe we just use
  the glass thingy"
- 10-05: "**the contrast between the buttons and the app itself is a bit
  lacking**; they're quite similar in color"

**Type and the story page**

- 09-27: "is our Font usage consistent? … the font from the map view seems to
  be different from the font used in the journal/settings"
- 10-01: "this page is just a **mess of different font sizes**"
- 10-03: "tons of different font sizes and formattings which just causes
  clutter … maybe … some kind of **custom delimiter**"
- 10-03: "for any quotes/then/now kinda thing … can we **take inspo from
  markdown**?"
- 09-30: "the memory unlocked page … still feels a bit... **lackluster**? …
  improve the look and feel and entertainment value"
- 10-06: "the memory creation view/screen/flow is **quite ugly and not
  intuitive** … it has to be a wonderful experience and a bit simpler"

**Copy and tone**

- 09-24: "too flowery"
- 09-27: "yuck, remove the stand here to read it text"
- 09-27: "should be more lenient and **not disappoint the user ever**"
- 10-01: "it sounds kinda dry rn"
- 09-26: "the add button needs to look more fun and indicate what it is … no
  need for a text … a **dedicated custom icon**"

**Layout**

- 09-26: "signup/onboarding … beautiful and elegant ui/ux, **simple as
  possible**"
- 10-01: "only have **1-2 buttons that become different things** depending on
  what the user is doing"
- **Core actions are one tap.** Add and Journal are never behind a hub or
  menu.

## 5. Tried and thrown out

- **Palettes**, in order:
  1. Tailwind zinc + amber.
  2. Stamp red.
  3. Ochre ("did not read warm enough").
  4. Teal brand + blue route ("teal works with neither").
  5. Ember `#B83A12` + bright gold.
  6. Gold / emerald / purple (current).
- **Black** pins and buttons ("not fun").
- **Fonts:**
  - Fraunces + IBM Plex Mono with uppercase labels (the "instrument" look).
  - Soft Fraunces + Figtree.
  - A WoW quest font + parchment texture: muddy brown, reverted.
  - Optima ("not a fan").
  - Then one rounded sans. A story-only serif is still the founder's open call.
- **Glass:**
  - Blurred translucent white: unreadable, read as an "AI tell".
  - Merged glass shapes ("not a fan").
  - A paper frost tint at 1.01:1 contrast.
  - The current rule: system Liquid Glass only over the map.
- **Pins:**
  - Five ink states with a shape per layer ("too complicated").
  - A mini padlock.
  - Lockets per era.
  - The compass unlock for every locket.
- **Route:** an animated dashed loop, and a grey line ("ugly and gray").
- **Buttons:** a 4 pt "ledge" lip, removed after one day.
- **Navigation:** a Pokémon-GO hub button (core actions ended up behind it),
  a left drawer, streaks in the walks view.
- **Other directions:**
  - Assassin's Creed II: "cold and sci-fi".
  - Neomorphism, skeuomorphic textures and a dark map theme, all rejected in
    docs/09.
  - Confetti, keys, embers and loot.
- **The memory as a small card:** "why did we move the memory unlocked view
  to just be a card? not a fan."

## 6. Constraints a redesign must keep

- Every text pair ≥ 4.5:1 in both modes (`tests/test_palette.py`).
- The map stays quiet: muted, POIs off. **Pins are the subject.**
- Don't cover the Apple Maps attribution (bottom-left).
- **One kind of pin**, the locket. Its states are keyhole vs plain, and lit
  (in reach) = bigger + emerald halo.
- Core actions (Plan a walk, Add, Journal) are one tap from the map.
- The unlock is the playful peak. Everywhere else is calm by default and loud
  only for real progress.
- Light and dark both ship. Android gets the light palette only.
- A real person's memory reads as theirs ("Left by"). An extracted one is
  always marked "Retold by AI from ‹source›".
- Native controls where iOS has them: the account menu, action sheets,
  pageSheets, Apple's sign-in button.

## 7. Open tensions and questions

1. **Cozy nature vs. jewellery.** The first brief was Stardew-cozy, warm and
   green. What got built is luxe gold lockets with emerald and purple on a
   cream map. Green survives only as "openable".
2. **Game vs. restraint.** "Feel like a game" keeps coming back, and so does
   "too much gamification". Where does the game feel live besides the unlock?
3. **The brand lags behind.** The ember icon/splash predates the gold, and
   the dark tile is muddy. The winding-path / gust-of-wind logo idea was never
   explored.
4. **The font** was picked to match Apple Maps, not to be expressive. Is
   there room for a story serif, or a display face for titles?
5. **The dark map is cool navy/purple** (05-home-dark), which fights warm gold
   on dark brown paper.
6. **The dive flashes white in dark mode.** Frame 13f shows a bright paper
   flash between the open locket and the story, in dark mode.
7. **Buttons vs. ground contrast** (10-05): the quiet buttons and the paper
   are close in value.
8. **Submit** is mid-redesign and still "not wonderful yet".
9. The walk stops' done / here / next / later states are not designed yet.
10. **Stale guidance to ignore:** the `locket-variations` skill still cites
    Fraunces, Plex Mono uppercase and seal `#c0462b`. Parts 2 and 5 of
    docs/09 argue against glass but are superseded.

## 8. Prompt to start a design agent with

> Read `docs/design-brief/README.md` and look at every image in
> `docs/design-brief/screens/`. Then propose a visual direction for Memory
> Lane that keeps the constraints in section 6 and resolves the tensions in
> section 7. Give two or three distinct directions first: name each, show a
> palette (light and dark) with contrast checked, a type pairing, button and
> card treatments, the locket pin on the map, and the unlock moment. Mock the
> home map, the walk card, the in-reach locket, the open story and the Submit
> screen in each. Say what you would change in `mobile/src/theme.ts` and
> `mobile/UI.md` to get there. The founder's taste is in section 4. Weigh
> "fun/unique", "not sterile", "not AI-y" and "like a game" over safe
> defaults, and do not bring back anything in section 5 without saying why it
> would work this time.

## Retaking the screenshots

The capture recipe, for after a redesign:

1. Use a second simulator, so a running dev session isn't disturbed.
2. Start a private API and Metro so the account is a free one. The dev API in
   docker sets `DEV_SUBSCRIBED=1`, which hides the paywall and the PLUS
   themes.
   ```bash
   DATABASE_URL=postgresql://memorylane:memorylane@localhost:5432/memorylane \
     ROUTING_URL=http://localhost:5001 DEV_SUBSCRIBED=0 UNLIMITED_WALKS=0 \
     venv/bin/uvicorn api.main:app --port 8091
   (cd mobile && EXPO_PUBLIC_API_URL=http://localhost:8091 npx expo start --dev-client --port 8082)
   xcrun simctl spawn <sim> defaults write com.PLACEHOLDER.memorylane RCT_jsLocation localhost:8082
   ```
3. Drive the app with throwaway Maestro snippets, borrowing selectors from
   `.maestro/*.yml`. Watch out for two things:
   - `takeScreenshot` writes under `~/.maestro/tests/<run>/`, not the
     working directory.
   - A long-press on a pin stands you on it (dev builds only).
4. Grab animations by firing `xcrun simctl io <sim> screenshot` in a loop
   while Maestro holds the locket.
5. Convert to 804-px JPEG with `sips` (PNG was 54 MB).
6. Afterwards, delete the throwaway device's rows from the dev database. Its
   unlocks, routes and heart are real rows.
