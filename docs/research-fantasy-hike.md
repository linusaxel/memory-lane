# Research: gear, exploring and story for a walking RPG

2026-10-11. After *The Locket-keeper* was built and reverted. The founder plays
RPGs; what pulls them is progression (better gear, dressing up the character)
and exploring, tied together by a story. Question: what does Fantasy Hike do,
and how do walking games make gear, exploring and story work? Adds to
`docs/research-progression.md` and `docs/research-prior-art.md` and does not
repeat them.

## Fantasy Hike

A LOTR-style step counter by Forge7 AB (Bara, by Malmö; one developer, side
project since 2015). iOS 2021-10-02, Android about 2024-12. Sources: the App
Store listing and version history, 708 US reviews from its RSS feed
(2021-10 to 2026-10), the [Reddit launch post](https://www.reddit.com/r/lordoftherings/comments/q9w86o/i_made_a_lotr_inspired_step_counter_app_for_nerds/)
and [The Verge](https://www.theverge.com/24065451/fantasy-hike-app-fitness-tracker-walking-health).

- **One route, no RPG systems.** Steps from Apple Health move a halfling
  1,779 miles from the Shire to "Mount Fire". Short text events on the way
  and an illustration per region. No combat, gear, loot, levels or classes.
  Customisation is a choice of avatars (v2.0, 2024).
- **The pacer is the hook.** Mr. Underhill walks Frodo's book timeline in
  real time from your start day; Jon Snowflake and Hairyfoot Potter walk at
  other paces. The most-praised feature.
- **Scale.** 4.83★ from 14,979 US ratings; Google Play 100k+ installs, 4.8★.
  The one Reddit post scored 7,477 and led to The Verge piece. No revenue
  figures anywhere.
- **Money.** Free for 1 mile a day; Unlimited Distance $6.99 once (was
  $3.99); Premium $1.99/mo to $9.99/mo for friends' stats; rewarded ads for
  more distance since v2.4 (2026-09).
- **Reviews (469×5, 88×4, 51×3, 46×2, 54×1):**
  - Loved: a goal measured in years ("1780 miles in 3 years and one month"),
    the race against Underhill, paying once, the near-miss names.
  - About 205 mention the cap or paywall, 92 of them at 1-3★: "This app has
    my completion date for 2036"; "pay to hike". Moving friends to a
    subscription read as "good but greedy".
  - Sparse beats: "Not worth $15 to be told 'You pass a group of trees'...
    every 10-20 miles".
  - The end is a cliff: "Dud ending... no fanfare... I just walked 1780
    miles". Dozens ask for a second route; finishers restart the same one.
  - **Gear: none of 708 ask for it.** Two ask for a customisable avatar.

## Gear and dressing up

| App | Gear | Figure |
|---|---|---|
| Dragon Quest Walk | Stat weapons and armour from a paid gacha with a pity card; free gear from monster drops | ~$2B lifetime by 2024-04; 545 min/week a player vs 192 for Pokémon GO ([Sensor Tower](https://sensortower.com/ja/blog/dqw-leads-geolocation-games-in-japan)). One player pulled 200 times for one weapon ([Dengeki](https://dengekionline.com/articles/216348/)) |
| WalkScape | RuneScape-like: steps buy travel and crafting; tools raise the odds of fine materials; cosmetics from achievements | Closed beta, 8.38B steps logged; "no MTX, no ads, no pay-to-win", one-off plus online subscription planned ([walkscape.app](https://walkscape.app)) |
| The Conqueror | Real routes (LOTR licence, Hobbiton to Mount Doom, 452 km); a physical medal per stage, the first stage's ring fits the last medal | "1M+ Conquerors", 87.93% completion; $49.99 a stage ([site](https://www.theconqueror.events/)). $80M a year is one unconfirmed profile |
| Pikmin Bloom | A Pikmin's costume comes from the kind of place it was found: a chef's hat at a restaurant | Never sold; the outfit is a record of where you walked ([wiki](https://pikminwiki.com/Special_Decor_Pikmin)) |
| Pokémon GO | Style Shop, 50-150 coins; some items behind level or medals | The 2024 avatar overhaul changed bought items: "the worst in the history of updates", refund requests ([Dexerto](https://www.dexerto.com/pokemon/niantic-let-me-pay-for-my-old-pokemon-go-avatar-2653132)) |
| Monster Hunter Now | Stat gear crafted from hunts; free layered armour (looks only) since 2024-03 | Revenue still fell yearly (see research-progression) |
| Finch | Habit earns stones, stones buy the bird's clothes; subscription on top | 4.95★ from 550k+ reviews |
| Habitica | Gold buys class gear with stats; subscribers get a monthly cosmetic at a shown price | The one random sink is paid in gold, not money |

- **Customising binds you to the character.** Players who customised
  identified more with their avatar and played longer by free choice
  (Birk et al., CHI 2016); it cut
  drop-out in a three-week daily exercise ([Birk & Mandryk CHI 2018](https://doi.org/10.1145/3173574.3174234)).
  No study ties it to months of retention in a commercial app.
- **Showing off pays socially, paying to win does not.** In Habbo, buyers of
  visible items made 13.2 friends against 5.1 ([Psychology of Games](https://www.psychologyofgames.com/2015/08/when-the-pay-to-win-button-backfires)).
- **Rules.** Paid random items need odds shown (Apple 3.1.1); a physical
  medal is sold outside in-app purchase (3.1.3(e)). Denmark calls a loot box
  gambling only when the prize turns into money
  ([Folketinget 2022](https://www.ft.dk/samling/20211/almdel/sau/spm/704/svar/1907545/2621968.pdf));
  the EU Digital Fairness Act may ban them where minors play.

## Exploring

- **CityStrides** counts a street when your track passes within 25 m of 90%
  of its nodes. 10,675 people finished 51,089 streets on Global Running Day;
  one runner finished all ~8,000 of Birmingham's ([rule](https://community.citystrides.com/t/about-the-node-street-and-city-data/19802)).
- **Tiles.** VeloViewer, Squadrats and Statshunters count 1.6 km squares.
  VeloViewer's Max Square was too punishing and got a forgiving Cluster
  measure ([VeloViewer](https://blog.veloviewer.com/veloviewer-explorer-overview/));
  Squadrats cut each square into 64 so a commute still counts.
- **Ingress** counts distinct portals (Explorer: 100 to 30k) and first
  captures (Pioneer) ([fevgames](https://fevgames.net/ingress/ingress-guide/concepts/medal/explorer/)).
- **Pokémon GO.** 68% walked parts of town they would not otherwise
  ([Ipsos 2016](https://www.ipsos.com/sites/default/files/2016-08/Pokemon_GO_taking_over_people_lives.pdf)).
  Region-locked species are a long-running complaint, softened since. Routes
  (2023) were called half-baked.
- **Geocachers** rank collecting last, after nature, escape and a walk with a
  purpose ([Falcão 2017, n=613](https://comum.rcaap.pt/entities/publication/ad6cc15e-172d-4d43-bf34-287a18290e52/full)).

## Story across walks

- **Dragon Quest Walk** moves its story on shards earned by walking to a spot
  you pick, more the farther it is (about 4 at 100 m, 225 at 1 km); new
  chapters are released over time ([Dengeki](https://dengekionline.com/articles/51052/)).
- **Zombies, Run!** is one mission a run, weekly, "like a TV show that you run
  to": 400+ missions over ~11 seasons, 10M downloads by 2025; newcomers catch
  up on the backlog ([PocketGamer.biz](https://www.pocketgamer.biz/novelist-naomi-alderman-reacquires-zombies-run-from-former-owner-olivex)).
- **The Walk** (Six to Start, NHS): 65 episodes unlocked by all-day steps, the
  goal per chapter fitted to the walker, about three months to finish.
- **Janet Cardiff's audio walks** are the place matching the recording, not a
  plot.
- **Evidence.** No trial compares story, completion and rewards for walking.
  A story raised steps 42% a session in children (n=22,
  [JMIR 2020](https://jmir.org/2020/3/e17994)); points and levels added about
  500 steps a day at a year ([BE ACTIVE](https://www.acc.org/latest-in-cardiology/articles/2024/04/02/17/02/sun-8am-be-active-acc-2024)).

## What it means here

1. **Gear changes how you look, never what you can read.** No item opens,
   speeds up or hides a memory. The gate decides that, alone.
2. **Gear comes from places.** Pikmin's rule: a sailor's cap from a Nyhavn
   memory, a printer's apron from a printing house. The outfit is a record of
   where you stood, so it cannot be bought.
3. **Sets over a district.** "Christianshavn sailors", completed over several
   walks, like the Conqueror's ring that fits the last medal. A physical pin
   for a finished set is the proven paid lever, later.
4. **Count memories, not streets.** "Vesterbro: 11 of 34" is finishable at
   ~30 a km², shows what is left without saying where, and is "walked" short
   of 100%.
5. **A thin story between the memories.** One narrator, written once per
   district or era, links the stops; a walk is a chapter that ends on a hook.
   A missed week never blocks the next one.
6. **A pacer.** Fantasy Hike's best feature is someone to race. Here: a
   teller who walked it, or your own last walk.
7. **Plan the end.** A finished district gets fanfare and says what is next,
   and reopens when new memories land.
8. **Dress up on day one.** Identification comes from choosing the look.
9. **Never sell randomness, never change what someone owns.**

**Caveat:** Fantasy Hike's 15k ratings came with no gear at all, and its
players asked for routes, friends and an ending. Gear is the founder's pull,
not yet a walker's. Test it with walkers before building it (the
Locket-keeper lesson).
