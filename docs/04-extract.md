# Memory Extraction

## Purpose

Process transcripts through LLM to extract location-based memories. This is the core value-creation step.

## Chunking Strategy

### Parameters
- **Chunk size**: 4 minutes (configurable via `CHUNK_MINUTES`)
- **Overlap**: 30 seconds (configurable via `CHUNK_OVERLAP_SECONDS`)

### Rationale
- 4 minutes ~ 800-1000 words, well within context window
- Overlap prevents missing memories that span chunk boundaries
- Time-based chunks align naturally with video structure

## Chunk Format

Input to LLM includes timestamp markers for accurate `timestamp_start`:

```
[0.0] Welcome to the show. Today I want to tell you about
[5.2] a trip I took to Tokyo last year. I was walking through
[10.5] Shibuya, and there's this tiny ramen shop...
```

## Extraction Fields

For each memory, the LLM extracts:

| Field | Description |
|-------|-------------|
| `place_name` | Human-readable name (e.g., "Cafe de Flore, Paris") |
| `place_query` | Dedup key and search string (e.g., "Cafe de Flore Saint-Germain Paris France"). A unique index makes this the identity of a place. |
| `country` | ISO 3166 two-letter code. Routes to national geocoders (none since DAWA was retired) |
| `address` | Street and number if the source names one, in today's spelling. With `venue`, what the geocoders place; `lat`/`lng` is the fallback ([why](10-decisions.md#the-llm-names-the-place-free-geocoders-place-it)) |
| `lat` | Latitude, estimated by the model. A memory without coordinates is filtered out of every API query. |
| `lng` | Longitude, same. |
| `timestamp_start` | When place is first mentioned (from [timestamp] markers) |
| `summary` | 2-4 sentences capturing the story - who, what happened, the vibe. Conversational, not a summary in the report sense. |
| `quote` | The best line about the moment, verbatim, at most 25 words, in its own language. `grounded()` checks it against the chunk like `place_words`, and an unfound one is set to null without dropping the memory. Shown under the summary ([why](10-decisions.md#the-open-story-has-a-shape)) |
| `quote_by` | Who said or wrote it, by name, or null |
| `tags` | 1-5 categories: food, travel, history, culture, adventure, romance, nightlife, nature, art, music, sports, business, personal |
| `location_precision` | exact (~50m), street (~200m), neighborhood (~1km), city (~10km) |
| `confidence` | high, medium, or low |

## Merge Logic

Memories for the same place within 60 seconds are merged:
- Time range extended to cover both
- Summaries combined
- Tags deduplicated

## Filtering

- Only **high** and **medium** confidence memories are saved
- Low confidence memories are discarded (unlikely to geocode well)

## Expected Output

```json
{
  "memories": [
    {
      "place_name": "Fuunji Ramen, Shibuya",
      "place_query": "Fuunji ramen Shibuya Tokyo Japan",
      "lat": 35.6894,
      "lng": 139.7005,
      "timestamp_start": 248.2,
      "summary": "The host describes finding a tiny ramen shop...",
      "tags": ["food", "travel"],
      "location_precision": "exact",
      "confidence": "high"
    }
  ]
}
```

## What it costs

`python -m pipeline.cost --since <day>` divides Anthropic's bill for those
days (Admin Cost Report API, needs `ANTHROPIC_ADMIN_KEY`) by the memories made
in them. Web search, page reads and thinking are all included. The target is
at most $0.50 a memory. The table below predates it: measured from the console
balance, when Sonnet 5 extracted and nothing was fact-checked or enriched.

| Run | Episodes | Video | Memories | Cost | $/memory | $/episode |
|---|---|---|---|---|---|---|
| 2026-09-27, Københavnerliv pubs, walks, place history | 12 | ~6.5 h | 48 | ~$2.00 | $0.04 | $0.17 |
| 2026-09-27, Københavnerglimt cinemas, hospitals ×2 | 3 | 1.3 h | 41 | ~$0.70 | $0.02 | $0.23 |

The first row's window also held a ~$0.80 classifier replay and Haiku screens
($2.83 in all), subtracted by the replay's own token count.

Yield decides $/memory far more than length does. The same channel's film
talk and festival episodes gave 5 memories from three videos at ~$0.30 each,
and local-TV guided tours (Bispebjerg, NTV Nørrebro) about 1 an hour. Budget
by the source's `mem/h` in `sources list`: roughly $0.30-0.50 an hour of video,
so a 30 mem/h history series is ~$0.02 a memory, a 6 mem/h one ~$0.05, and a
1 mem/h one ~$0.40.

## Memory quality
The summary is the product: somebody standing on the spot, on a phone, outdoors.
Measure before and after any prompt change — extraction costs money and you get
one shot:

```bash
python -m pipeline.quality
python -m pipeline.quality --compare candidate.txt   # same 10 chunks, both prompts, side by side
python -m pipeline.quality --labels                  # the judge against the corpus read's verdicts
```

An extracted video has no transcript left (docs/10, *A video's transcript is
deleted once it is extracted*), so `--compare` on video samples only videos
not yet extracted; books keep their text.

Baseline on the 224-memory corpus, all four found by reading it rather than
guessing, and all four now addressed in `SYSTEM_PROMPT`:

| | | |
|---|---|---|
| anonymous subject | 55% | "The speaker drove the van…" instead of the name |
| talks about talking | 20% | "He describes…" reports the recording, not the event |
| not past tense | 12% | "He's playing the Fillmore on the 14th" is a ticket ad |
| over 70 words | 32% | a summary of the conversation, not of what happened |

The prompt now bans the labels outright, rejects upcoming shows as hard as it
rejects hypotheticals, asks for 2–3 sentences, and carries four worked examples
taken from the corpus's own failures. It is structured with XML tags, gives
explicit permission to return nothing, and is sent as a cached block — it is
~1.2k tokens resent for every chunk, and a cached read costs 10% of input.

A fifth check came from the first Copenhagen video: **the spot test**. Would
the story lose anything pinned somewhere else? A nickname earned on a ski trip
fails; a bar that sank into the stream under it passes.
- The model answers it in `spot_test`, after quoting the place in `place_words`
  and before it names a venue.
- Code drops a fail, a quote that isn't in the chunk, and a `city`-wide pin.
- Every chunk also gets a brief of the whole video, so "the pub crawl" can say
  which one.

The reasons are in the [decision](10-decisions.md#a-memory-is-decided-before-it-is-written).

Grounded is not the same as interesting. Once per video, `worth_telling()` asks
six yes/no questions of every candidate that survived: the swap test, breach,
consequence, visible now, so what, and stands alone. Code keeps a candidate only
if the swap test and stands-alone both hold, plus 2 of the other 4, on a majority of three passes in different orders
([decision](10-decisions.md#a-story-has-to-be-worth-telling)).
Then `one_name_per_venue()` asks, once per video, which of the survivors' venue
names are one real place, so "Barbershop on Vognmagergade" and "Herrefrisør på
Vognmagergade" land on one pin
([decision](10-decisions.md#one-venue-one-name-per-video)).
`quality` also counts "someone", since the video usually gives a name or a
nickname. Spot relevance itself has no regex: read the output.

### Corpus read, 2026-09-29

Every visible memory (209) was read and scored against a rubric built from the
interpretation and locative-media literature. **About a quarter are worth the
walk.** The scoring was done by AI agents (Claude), one read per memory, not by
a person, so treat the counts as approximate. Each verdict is in
`tests/fixtures/walk_labels.json`: id, walk/maybe/skip, the total out of 10 on
the five criteria the scorers used (site, surprise, story, trace, standalone),
and flags. The fixes are in TODO.md, *Make memories worth the walk*.
A spot-check of 20 (7 walk, 7 maybe, 6 skip) held on every verdict and found
three flags missing: two `hall` for "Jørgen Let" (Leth), one `german`. They
are fixed in the file.

**Baseline for the judge** (`quality --labels`, 2026-09-29, 151 Sonnet calls).
Re-judging the 209, today's judge keeps 156: 48 of 52 walks, 41 of 55 maybes,
67 of 102 skips. Precision 31% (walk of kept), recall 92%. It drops a flag's
memories no more often than the rest: `stale` 0 of 6, `adv` 3 of 19, `priv` 7
of 16, `out` 13 of 32. That is the number Judge v2 has to beat: precision up,
recall held. By half (`--half`, even content ids tune, odd check): tune 29% /
89%, check 32% / 96%.

**Judge v2, measured and parked** (2026-09-30, 151 Sonnet calls). The rubric's
questions (incident, feeling, relates) plus three drop-gates
(`private_person` within living memory, `promo`, `relative_time`), with
Copenhagen archival examples from the tune half. The gates work: they dropped
`adv` 18 of 19, `priv` 13 of 16, `stale` 6 of 6. The story bar doesn't: at two
of incident, breach and feeling, check-half precision is 42% but recall 60%.
No bar held 85% recall above v1's precision, so v1 stays. The reason is in the
labels: of the ~28 skips per half the gated judge still keeps, 17–18 are
skipped only for `out`, `pin`, `p1000`, `dup` or `hall`. A judge reading a
summary can't see those. The launch-area gate, the dedup and grounding fix
them, and the judge is worth retuning after they land.

**The launch-area gate** (2026-09-30, docs/10 *One launch area*). The box
`55.60,12.45,55.74,12.66` catches all 32 `out` memories and no walk, plus
Ålebækken ×2 (pinned at 55.80, probably wrongly) and Bakken in Klampenborg.
The 35 were hidden on the dev database with the SQL below. Visible labelled
memories are now 52 walk, 54 maybe, 68 skip: 30% worth the walk, up from 25%.

**Retellings** (2026-09-30, docs/10 *A memory is not saved twice*).
`python -m pipeline.dedup --memories` found 6 on the visible corpus, and all 6
it hid are labelled `dup`, with no walk lost: Hedebygade, Toldbodgade 67,
Gammel Toldbod, Centralhjørnet, Leonora's arrival at the Blue Tower, and the
Christiansborg fire (the walk kept, the skip hidden). It missed two pairs the
labels call duplicates, Flyvergrillen and the Glud & Marstrand sabotage.
Visible labelled memories are now 52 walk, 52 maybe, 64 skip: 31%.

```sql
UPDATE memories m SET hidden = TRUE FROM places p
WHERE p.id = m.place_id AND NOT m.hidden
  AND NOT ST_Intersects(p.coordinates::geometry,
                        ST_MakeEnvelope(12.45, 55.60, 12.66, 55.74, 4326));
```

**The archival prompt** (2026-09-30, `quality --compare`, ~40 Sonnet calls).
`HISTORICAL_SYSTEM_PROMPT` took the video prompt's rules: the three deciding
fields first, 40–70 words, lead with the surprise, a role for every name, the
venue in today's local name, a visit fails, and three worked examples (4545 a
pass; the Halberstadt monastery and the coronation on "the castle in a lake"
fails). On 15 book chunks it kept 8 against 16. Of the 12 it dropped, 8
were visits and salons abroad or outside the city (Berlin, Dublin Bay,
Streit's Hotel, Kronborg) and 4 were thin Copenhagen scenes (Andersen's
Armida bill, a walk to Frederiksberg). It found 4 the old prompt missed:
three Kasino carnival fires and Andersen's rent-lowering tears. Venues came out
Danish ("Det Kongelige Teater"). On 12 Historisk Atlas chunks it kept the
same 11, in tighter words. Existing memories are not re-extracted.

**Summary against its chunk, measured and not shipped** (2026-09-30). Every
labelled memory traces to its chunk (`extraction_chunks` holds the reply that
wrote each summary, verbatim), so a check was replayed over all 209, one call
per chunk, with the video's brief as context. Three designs:
- Haiku rewriting the summary: 55% changed, 3 walks dropped (Ringkaféen,
  Hedebygade, Nyvartov), summaries replaced by verbatim source, "Venue, City:"
  prefixed.
- Haiku naming `{wrong, right}` fixes that code applies: 75% changed, Danish
  and German pasted into English ("det tyske militær"), comments ("(confirmed
  in transcript)"), whole passages swapped in.
- Sonnet, same fixes, told "only what a reader would believe wrongly": 70
  changed, 19 of 52 walks. Real catches: Kristensen, Politiken, the
  Spanish-American war (4482), Kronborg (4543), Count Horn's name. But it cut
  the father and the boy from 4545, the best walk; echoed caption mishearings
  back as fixes (Toldbodgade to "Tøjboggade", Mor Jane to "Moriane"); cut what
  the brief supplied ("began in 1996"); and left "bars,." behind.

An automatic edit that hurts the best walk is worse than the ~20 errors it
fixes. What worked is finding them, not fixing them.

**Source triage** (2026-09-30, by hand, on the dev database).
Kunstindustrimuseet and Frederikshospitalet, one building 477 m apart as two
`llm` pins, are one place at Bredgade 68 (DAWA); the two Glud & Marstrand rows,
16 m apart, are one. The Blue Tower's seven visible scenes all stay: many
memories on one spot are fine when they are not the same content (docs/10, *A
memory is not saved twice*). Flyvergrillen 4468/4469 and Glud & Marstrand
4954/4957 are not retellings either: two stories, and two sabotages two
months apart. The travel volumes and Liebenberg were already paused; Carl
Møller stays, since the new archival prompt found its Kasino fires. Visible
labelled memories are unchanged at 52 walk, 52 maybe, 64 skip: 31%.

**Carl Møller re-extracted with the archival prompt** (2026-09-30, one book
first, ~100 calls). A founder's exception to *Never re-extract*: its 28
chapters were reset and run again, the old memories left visible. It saved 8:
five new scenes (the Charlottenborg torch march, the whale that collapsed on
twenty guests, the carousel with Tietgen dizzy on a seat-arm, the Kasino
kitchen fire, Krohn tearing down his own burning set) and three retellings
the save-time check missed. It missed them because it searched 150 m around
the model's pin, which was 474-1,020 m from the Studenterforeningen and
Kasino already saved, and the venue then snapped each one onto the first
telling's pin. `_landing()` now searches where the memory lands. The three,
and the old carousel telling, are hidden; Kasino's two `llm` pins are merged
into the hand-placed one on Amaliegade. The book shows 12 memories, up from 8.

**Oehlenschläger vol. I re-extracted the same way** (2026-10-01, source 204,
34 chapters). It saved 13. Nine are new scenes: the boy drilling with a sooty
toy rifle under the Crown Prince's window ("But where is Adam today?"), the
comedies at Frederiksberg ended by a rotten apple, fleeing his own
confirmation, weeping in Elers' Kollegium's library until Ørsted found him,
Ulfeldt's shame column, the 1796 fire, Bakkehuset, the camphor nymphs on
Kongens Nytorv and meeting Steffens at Richter's. Four are retellings: the save-time check
hid the old Christiansborg fire for the new one, and the dog, the grocer
and the gallows were hidden by hand, keeping the better-placed telling. The
book shows 22, up from 13. No German place name survived this time and
nothing landed abroad, but five pins are still 1000 m guesses (Ulfeldts
Plads, "city centre", Bakkehuset, Kongens Nytorv twice).

**Andersen re-extracted** (2026-10-01, source 202, 27 chapters, about 8
minutes). It saved 6, all photon or wikidata pins at 50 m: three theatre
scenes on his arrival (the playbill he took for a gift, the sausage sandwich
while he wept at Paul and Virginia, being dragged to the footlights in his
confirmation coat), two at Admiral Wulff's in Amalienborg, and Thorwaldsen's
return. The save-time check hid both old tellings these replaced, because
they were on the same place rows, so nothing was hidden by hand. The book
shows 10, up from 5.

Flags: `out` outside Copenhagen, `pin` a street, district or shared centroid,
`p1000` a named site at 1000 m, `wrong` the wrong place, `dup` a near-duplicate,
`ctx` a name or speaker never introduced, `desc` no incident, `adv` present-day
promotion, `priv` a private person's death, health or crime, `hall` a likely
factual error, `stale` relative time, `obsc` only for specialists, `german` a
German place name left in, `set` only set at its place (any place of the kind
would tell it the same; added 2026-10-03).

The verdicts used five criteria from 0 to 2 each: site, surprise, story, trace
and standalone. A total of 7 or more with no disqualifying flag was a walk, 5–6
a maybe. The research rubric below came in at the same time and is the one to
build the next judge on. It swaps standalone for feeling and then-vs-now, and
scores six criteria from 0 to 2 each:

| Criterion | 2 means | Source |
|---|---|---|
| Site-lock | it happened at this doorway, not "in Copenhagen" | Reid et al., [magic moments](https://dl.acm.org/doi/10.1145/1178477.1178529) |
| Visible trace | the text points at something still there | English Heritage [plaque criteria](https://www.english-heritage.org.uk/visit/blue-plaques/propose-a-plaque/) |
| Incident | a scene with people and stakes, not names and dates | [VoiceMap](https://docs.voicemap.me/tour-publishers/writing-scripts-that-make-listeners-feel-something/), Made to Stick |
| Surprise | "wait, *here*?", a small gap you want closed | [Tilden](https://mylearning.nps.gov/library-resources/tildens-six-principles-ace/), Loewenstein 1994 |
| Feeling | awe, danger, anger, absurdity | Berger & Milkman, [JMR 2012](https://journals.sagepub.com/doi/10.1509/jmr.10.0353) |
| Relates | then against now, tied to the walker | Tilden, Ham's [TORE](https://panorama.solutions/sites/default/files/Ham-TORE_model-2008.pdf) |

A total of 9 or more out of 12 is worth the walk, 7–8 is filler, and 6 or less is cut.
`pipeline/walk_score.py` scored every extracted summary on it into
`memories.walk_score`, which picks a walk's stops (docs/10, "A walk picks its stops by the rubric").
Since 2026-10-05 it asks one holistic question instead, with these criteria as
what raises and sinks a story (docs/10, *The walk score asks one question*).
Whatever the total, site-lock must score at least 1, and trace and relates can't
both be 0. Being on the spot adds imagery, not emotion or recall (Karapanos et al.,
[IwC 2012](https://www.sciencedirect.com/science/article/abs/pii/S0953543812000367)),
so a story needs the place and the telling both.

| Source | Walk | Maybe | Skip |
|---|---|---|---|
| Københavnerglimt (41) | 14 | 16 | 11 |
| Københavnerliv (71) | 16 | 20 | 35 |
| Local TV (3) | 0 | 1 | 2 |
| Books (81) | 20 | 12 | 49 |
| Historisk Atlas (13) | 2 | 6 | 5 |
| **All (209)** | **52** | **55** | **102** |

The best examples:
- 4408: the Woodstock counter that survived because a regular had mortared it in.
- 4545: a suicide on Frederiksberg Allé, seen by the boy Oehlenschläger.
- 4528: Andersen praying on the empty Royal Theatre stage.
- 4482: staged Boer War footage in the circus building.
- 4470: an airport rampart against ice-cream eaters.

**A line in their words** (2026-10-01, ~125 Sonnet calls). Both prompts
gained `quote` and `quote_by`, plus "end on what is still visible". Measured
with `quality --compare` at 20 chunks each:

- **Video:** 12 against 15 kept, which is chunk noise more than prompt: the old
  prompt kept two Trip Nørrebro stories, and the new one kept two DC Improv
  ones. The failure checks were flat (anonymous 1, meta 1; over 70 words 0
  against 1). 10 of 15 kept a quote, and they are the voice the summary
  cannot be: "der var altså nogle gange hvor man ikke nåede helt hel skinnet
  hjem" (Jokum Rohde), "This is the nicest man on the planet, Teddy." (Mark
  Normand).
- **Archive:** 19 against 19, the same places, every check at 0. The first
  draft quoted 11 of 19, and nearly all of them were the resistance
  register's own flat sentences, saying the summary again in Danish. The
  prompt now says a register has no voice. That left 1 of 19: a saboteur's
  "nu sprænger bomben".
- **The Weather Girls card text,** standing in for the post (which is in
  neither the repo nor the database): kept 3 of 3.

Books were not sampled. They are where a memoirist's quote should show up.

**The north star: the Weather Girls.** A post by Nicolas Cosedis (Facebook,
seen 2026-09-30) about the weather station on Richshuset, Rådhuspladsen, is what
a historical memory should read like. Written as a card:

> A giant neon thermometer runs up the tower above you. At the top, gilded
> figures by the sculptor Einar Utzon-Frank have told the weather since 1936:
> a girl on a bicycle in fair weather, and a girl with an umbrella and a small
> dog in rain. For decades they stood still. In 2024 they were regilded and
> began to move again.

On the research rubric it scores 10 of 12: site-lock 2, trace 2, incident 1,
surprise 2, feeling 1, relates 2. It works because you look up and it is still
there, it still moves, and the then against now is spelled out ("stood still
for decades"). The post runs ~400 words; cards ran 40–70 until 2026-10-04 and
now run to 180 (*A longer card*, below).

**Letting it pass** (2026-09-30, ~110 Sonnet calls). The archival prompt
dropped the post: "a building existing is not something that happened" couldn't
tell static description from a visible oddity with dated turns (made, stopped,
restored). `HISTORICAL_SYSTEM_PROMPT` now qualifies "a thing still there with a
life of its own" and says a tower, spire or portal with a build date is not one.
- The post itself: dropped before, kept 3 of 3 after.
- A held-out neon sign told in the same architectural register: dropped
  before, kept 3 of 3.
- Four held-out oddities with a plain event in them (Lurblæserne, the stork
  fountain's midwives, the Nyhavn anchor, Rundetårn's ramp) passed before and
  after. Three plain descriptions (a historicism block, a Plesner villa, a
  restored fountain) returned nothing before and after.
- `quality --compare`, archive 20 chunks: 19 against 19, the same places.
  Books 15 chunks: 5 against 8. The losses are Hellebæk and Hamburg (outside
  the launch area), the thin Kasino quarrel, and Andersen's rent tears, from a
  chunk the old prompt itself leaves empty 6 times in 8.

The Weather Girls are not a worked example in the prompt. A version with them
in it kept 4 book memories and never kept that Andersen chunk
in 8 runs, and it would stop them working as a held-out test.

What sank the rest, roughly how often:

| Failure | Count | Example |
|---|---|---|
| Near-duplicate of another memory | ~50 in ~17 clusters | Ditlevsen ×6, the Blue Tower ×8, 4624/4625 |
| Vague or wrong pin | ~40 | the Royal Theatre at 1000 m; 4564 is Frederiksborg, not Frederiksberg |
| A description, not an incident | ~40 | "opened X, closed Y, now Z" |
| Speaker or name never introduced | ~50 | "Christine", "the host", Rahbek |
| Outside Copenhagen | 32 | Oehlenschläger's travels, 10 of 11 abroad |
| Factual or speech-recognition error | ~20 | Tom "Christensen", lupus called cancer |
| Present-day promotion | ~15 | 4471, 4475 |
| A private person's death, health or crime | ~10 | 4435, 4466 |
| Relative time that will go stale | ~7 | "last summer" |

Then against now, the contrast the product ranks by, is almost never stated,
and `contrast_score` looks like a default (0.7 on 11 of the 13 Historisk Atlas
entries).

The books were re-extracted on real credits (2026-10-01, above); the rest of the
corpus is as labelled.

### Research, 2026-10-02

Three questions: what makes the next 30% of memories worth the walk, which
sources have more such stories, and what the literature says about the
technique. The ranked fixes are in TODO.md, *Make memories worth the walk*.

**The two biggest failures are made by chunking.** "Name never introduced"
(~50) and near-duplicates (~50) both come from reading a video four minutes
at a time. The brief patches the first; merge, the save-time check and the
venue folding patch the second. A Sonnet-class model reads a whole episode
(8–15k tokens) in one cached call, and Anthropic's long-context guidance is the
document first, the instructions after, and quotes asked for
([long-context tips](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/long-context-tips)).
That is measured below, *A video read whole*.

**Technique.**
- Generate more candidates than you need, then rank them. Highlight detection
  lets the model rank candidates and pick real transcript sentences rather than
  commit up front (RankCut, [IUI'26](https://www2.informatik.uni-hamburg.de/wtm/publications/2026/SLCWBW26/iui26_Shah-et-al.pdf)).
  Today's judge applies an absolute bar per video, so a dull video still ships
  its least dull story.
- Judge pairwise, in both orders, and keep only the verdicts that agree. About
  a third of judge verdicts flip with order
  ([Zheng et al. 2023](https://arxiv.org/abs/2306.05685)). Judges also prefer
  longer text ([length-controlled AlpacaEval](https://arxiv.org/abs/2404.04475)),
  which the 40–70 word cap already blocks.
- Calibrate the judge on a person's labels. Off-the-shelf judges agree with
  people on story quality about 73% of the time at best
  ([LitBench](https://arxiv.org/pdf/2507.00769v1)), and the criteria only become
  clear once you read outputs ("criteria drift",
  [Shankar et al. 2024](https://arxiv.org/abs/2404.12272)). Our labels were made
  by agents, and `memory_reviews` holds no rows.
- Never take coordinates from the model. On land grants, the best LLM had a mean
  error of 23 km ([arXiv 2508.08266](https://arxiv.org/abs/2508.08266)). What
  works is to fetch candidates from a gazetteer and let the model choose between
  them, resolving all of a text's places together
  ([Hu et al.](https://ceur-ws.org/Vol-3969/paper6.pdf)). The geocode chain
  filters single hits; it does not offer a choice.
- The Citations API can't be combined with a JSON schema (400), so a quote
  checked in code (`grounded()`) remains the right tool.
- Batches are half price and stack with caching
  ([batch processing](https://platform.claude.com/docs/en/build-with-claude/batch-processing)).
  `pipeline.batch` sends the web research through them too: a plaque's before
  extraction, each memory's enrichment after (docs/10, *Extraction is
  batched*). The searches themselves are not discounted.

**Sources.**
- The craft rule from audio tours: tell them what they can't see, and people
  rather than places
  ([VoiceMap, Darbyshire](https://blog.voicemap.me/2026/03/how-to-tell-a-story-15-script-tips-from-tom-darbyshire/)).
  Detour, Autio and HearHere all paid editors. Their moat was curation, and their
  weakness was coverage outside the hero cities.
- Wikipedia (da GeoSearch hits 500 articles within 500 m of Rådhuspladsen) and
  Wikidata (P625, inception, significant event) are dense but encyclopedic.
  Alone they fail as `desc`; as enrichment they supply the then-against-now line
  that is almost never stated.
- Public-domain memoirs (Runeberg, ADL) are legally clean, and books already
  give the most walks (20). The Stadsarkiv's erindringer are still the prize,
  blocked on permission. YouTube is "No, as built" (docs/10), so it is for
  finding stories, not a backbone.
- OSM `inscription=*` and plaques are cheap. Open Plaques is thin in the
  Nordics. HMDB and Atlas Obscura forbid commercial reuse.

**A video read whole, measured and not shipped** (2026-10-02, `quality --whole
5 --runs 2`, 40 Sonnet calls, ~300k tokens in, 70k out, roughly $1–2). The five
videos with the most labels (544, 545, 546, 592, 584) were each read as one
chunk, with the same prompt, brief, filter and judge, and nothing was saved. The
other side is the labelled memories, which are one draw of the 4-minute chunks
under older prompts, so the writing checks favour whichever side has the newer
prompt.

| | Chunked (labelled) | Whole, run 0 | Whole, run 1 |
|---|---|---|---|
| Kept | 57 | 39 | 31 |
| Walks found again | 15 of 15 | 13 of 15 | 11 of 15 |
| Anonymous, meta or "someone" | 10 | 5 | 1 |

- **It reads less.** It keeps a third to a half fewer memories, and from one draw
  to the next a video swings from 5 to 12, or from 14 to 8. That is the
  long-context loss the literature warns about: one reply has to cover an hour.
- **It loses walks.** Almindelig Hospital was missed on both runs, and
  Alexandra, Metropol, Trianglen/Nyvartov and Sundholm were each missed on one.
- **It writes cleaner,** but it reads cleaner partly because the prompt is
  newer than the labels.
- **It didn't remove duplicates.** Run 0 of 546 kept "Sankt Jørgens Hospital
  site" twice. Misheard names survive too ("Ørsundshospitalet").
- It found a few stories the chunks missed (Grand Teatret, Café Heimdal and
  Café Ægir on both runs, Søkvesthuset).

The ship bar was no walk lost on both runs, and it failed. Chunks stay. The fair
next measurement is chunked against whole under today's prompt, both drawn
twice. A middle course is also open, such as 15-minute chunks.

### Now, 2026-10-02

What does a person on a spot want that isn't history? Mostly "what's new or
different here": 72% of mobile information needs are triggered by place or
activity ([Sohn et al., CHI 2008](https://researchcommons.waikato.ac.nz/handle/10289/3657)).
Feeds of public records failed: EveryBlock gave permits and crimes by block and
closed in 2013, Patch lost over $300M, and Field Trip's nearby cards closed in
2019. Change told as a story has worked
([NYC storefronts](https://www.smithsonianmag.com/arts-culture/new-york-storefront-comparison-photos-180950376/)).
The decision is in docs/10, *The recent past is a memory*.

**KK's street-use permits** (`wfs-kbhkort.kk.dk/k101/ows`, layer
`raaden_over_vej_events_anonym_aktuelt`, Open Data DK terms, attribution).
On 2026-10-02 the layer held 9,344 current permits with dates and polygons:

- **Outdoor seating (3,237), not openings.** Starts come in December renewal
  waves (349 in Dec 2024, 660 in Dec 2025), and the layer holds no history.
  None of 10 off-season starts checked by hand turned out to be an opening:
  Café Malmö (a seamen's pub from 1870), Salling Kultorvet, Holberg no 19, a
  bike shop and a hair salon (shop displays share the type), and Balders Plads
  ApS (new owners of Soundtrack Café, CVR December 2025). Phoebe on Pilestræde
  may be new. An opening needs our own snapshots diffed over months, or CVR's
  registration date.
- **Film shoots (223 permits, about 36 productions), the find.** Each names
  the producer and often the film and the exact address:
  - Zentropa filming inside Det Kongelige Teater "for a feature film about
    HCA" (Nov 2026), where memory 4528 already has Andersen praying on the
    empty stage;
  - Miso Film shooting *Lyden af succes* at Ewaldsgade 3 and Hejrevej 26;
  - DR and TV 2 at the opening of the Folketing.

  These are dated, past tense once shot, and the thing that set-jetting tours
  sell. Productions sometimes park at one address and film at another, so read
  the description for the real spot.
- **Street events (187), for the expiring type.** Grønt Marked, Byens Lopper,
  an artwork on the ramparts in front of SMK.

**Foursquare OS Places** (Apache 2.0, monthly, `date_created`/`date_closed`)
is gated on Hugging Face behind a login and wasn't probed. Its `date_created`
is when Foursquare learned of a place, not when it opened.

### Corpus work, 2026-10-03

One session's changes to the dev corpus, about $3 of credits in all.

- **Walk scores for everything.** `python -m pipeline.walk_score --all`
  scored the 236 extracted memories (none had been). Against the 209 labels,
  walks average 7.1 and skips 5.6 (r = 0.45 with the hand total). The route
  now ranks by it: docs/10, *A walk picks its stops by the rubric*.
- **DAWA is gone.** `api.dataforsyningen.dk/adresser` answers 410 Gone, so
  every Danish address lookup since its retirement had failed quietly to
  the model's coordinate. Removed from the chain; Photon places the same
  addresses (OSM imported the Danish register).
- **Pins re-placed** with `python -m pipeline.repin --choose --apply`. Of 58
  `llm` places with a visible memory, the chain placed 3 addresses for free
  and the model's pick from the map's points placed 9 more (Vestre Hospital
  is Rudolph Berghs Hospital, Frauenkirche is Vor Frue Kirke, the Royal
  Danish Theatre is Gamle Scene). Each pick was checked on a map. Two traps:
  a street is never a candidate (Gammel Toldbod picked as Toldbodgade landed
  600 m off), and Wikidata's label search is prefix-only, so the full-text
  search near the guess (`nearcoord:`) finds "Frederiksberg Gardens". 47 are
  left, nearly all demolished cinemas, factories and hospitals.
- **What stands there now** for every building-level pin:
  `python -m pipeline.now` looked at 31 places with no refusal and
  confirmed 17.
- **Leonora Christina re-extracted** (source 203, 14 chapters). It saved 8.
  `dedup --memories --source 203` then paired 7, read by hand: 5 retellings
  hidden (the Mistress of the Robes, the pier, the betrothal day, La Rosche,
  the governor's gate), one kept as a different scene (the Dark cell), one
  already hidden. The book shows 10, up from 8.
- **Two new public-domain books** through the Gutenberg path, Copenhagen
  windows only: Jacob Riis, *The Making of an American* (10 windows, 2 kept:
  the stranger at Charlottenborg who was the king, schoolboys saluting
  Andersen on the ramparts) and Maurice Baring, *The Puppet Show of Memory*
  (15 windows, none kept: legation society, not scenes). Nexø's memoirs are
  public domain since 2025 but have no free digital text; Andersen's *Mit
  Livs Eventyr* would mostly retell source 202. On 2026-10-04 `now.py` also asks for points
within 25 m (a bar is a node, not an area), confirming by name only.
`--blank` over the 29 blank places confirmed 3 (Café Ægir, Ålholm Borgerkro,
Copenhagen Hotdog); the public server refused the other 26, which stay blank
for the next `--blank`. On 2026-10-09 the mirrors were no way round it:
kumi.systems and private.coffee returned 500 and maps.mail.ru 504 on a
one-point query. Against kumi, `--blank` (97 places: 32 blank, 65 never looked
at) got one answer, Københavns Rådhus ("Still ... since 1905"). The public
server then answered 20 of the other 96 and confirmed 13, all "Still" (Café
Lille Peter, Folketeatret, Vega, Magasin du Nord, Frederiksberg Rådhus since
1953); it refused 76. Two read wrong: "Field's, a parking" and "Nyhavn, an
attraction", where the point matched is not the building. A "Still" scores
0.2, so these sink in the ranking rather than rise; the ranking reads better
only where a "Now" lands, and this run found none. A self-hosted Overpass on
the Denmark extract is the fix that would hold.

The visible corpus went from 188 to 192 memories.

### What to look at, 2026-10-03

TODO.md's *What to look at* wants a line telling a walker where to look. It was tried on 40
visible memories (a stable sample, `md5(id || 'look')`): one Sonnet call
each, given the place name and the summary, asked for at most 12 words
pointing at something visible now, with no people, events or dates.

- **About 6 were real:** Kaj Nielsen's bull wrestlers on Palads, Vor Frue's
  spire, Blåtårn's footprint marked in the Christiansborg paving, the
  Sjæleboderne sign.
- **About 15 were filler:** "notice the facade above the entrance".
- **About 14 were invented,** mostly at places that are gone: the "vintage
  marquee" of the closed Løvebiografen, Chickegrill's "red curtains", graffiti
  at Lorterenden.
- **A few leaked the story:** "find the framed portrait", "the bar counter's
  mortar joints".
- 4 were empty, as asked when nothing is visible.

Not shipped, and no field added. A summary does not know what stands there
now, so the model fills the gap. Next time, ground it: only places whose OSM
`now` says the same place still stands (`places.now->>'same'`), and give the
model OSM's tags and Wikidata's description of the building, not the story.

### The place test, 2026-10-03

Half of the day's batch (Leonora Christina, Riis) only happened to be *set* at
its place: guards' abuse in the Blue Tower, La Rosche in the witch-cell, a
Mistress of the Robes' screams. Any prison would tell them the same. The
judge's `only_here` asked "swap in another place's name: does it become false
or pointless?", and for documented history a swap always makes it false, so
every memoir story passed. `walk_score` scored the summary without the place
name, and the labels marked three of these stories `walk`.

- **Labels:** a `set` flag (only set there) on 19 labelled book memories and
  today's 10; 4537, 4540 and 4543 moved from walk to skip. AI read, not a person.
- **Judge:** `only_here` is now a same-kind swap: moved to another prison, hall
  or street, does it lose something? Two examples, written fresh so they are
  not in the labels: Kongens Nytorv's sagging lead statue (yes), a Kastellet
  cell (no). `spot_test` asks the same, and a venue must be a spot a walker can
  stand at ("the ramparts" is not).
- **`walk_score`** now scores "place: summary".

| `quality --labels` | `set` kept | precision | recall |
|---|---|---|---|
| Before | 14 of 22 | 30% | 93% |
| "About the wall, gate, stair" | 3 of 22 | 34% | 74% |
| Same-kind swap (shipped) | 3 of 22 | 35% | 81% |

The first wording cut the hanged grocer on the avenue, Andersen on the empty
stage and the Kierkegaard plaque, so it was replaced. The shipped one still
drops 6 more walks than before; some are fair under the new bar (the horse fall
on the Esplanade, the bridge swim), some are not (the king guiding Riis at
Charlottenborg, Andersen at Bakkehus). One run each: the judge flips between
runs. The `spot_test` change is unmeasured: `quality --compare` on book chunks
is next (TODO, *The place test*).

**Amended 2026-10-07.** Someone famous at this exact spot now passes
`spot_test` and `only_here` (docs/10, *Famous people at a spot, and good is 6*).
The king guiding Riis at Charlottenborg is the kind this lets back in.

| Measured on the labels | Before | After |
|---|---|---|
| `walk_score --labels` AUC (judgeable) | 0.711 (0.847) | 0.680 (0.849) |
| `walk_score --labels` 7+ (of them walks) | 15 (13) | 14 (12) |
| `quality --labels` precision / recall | 41% / 52% | 42% / 52% |

One run each. The labels hold few famous visits, so these mostly say nothing
broke; the overall AUC dipped 0.03, inside the run-to-run spread. Re-extracting
K.B. Hallen (3692) moved no score: "X played this hall" is the hall doing its
job, not a famous person turning up somewhere. The rule is for a bar, a hotel,
a shop.

### The place test applied, 2026-10-03

- **`spot_test` measured.** `quality --compare --source-type book --sample 20`,
  the prompt before fdde988 against after: 11 kept each. The new one dropped a
  district standing in for a venue (Hauch's home, "Frederiksberg") and two
  stories only set at theirs (Fichte at Hufeland's, Jenny Lind in Hamburg); it
  added one of the same kind (Ryge's walk to Frederiksberg). Noise, not a loss.
- **The visible books re-judged.** `quality --visible --source-type book`
  (new) runs the judge over what is shown and prints what it drops: 52 of 70.
  Of the 36 labelled, 20 were skip, 8 maybe and 8 walk. 34 hidden after a read
  (`review --reject`): the 20 skips, 6 maybes and 8 unlabelled stories only set
  where they sit. Kept: the 8 walks, two badly pinned ones, and 8 unlabelled
  where the place is the point (Andersen at the theatre, Thorvaldsen's return).
- **Blue Tower is one place:** 4324 and 4325 merged into Wikidata's Blåtårn
  (5383), on the footprint in Christiansborg's paving. The user pin was 200 m
  off. `save_memories` now reuses a place on the same Wikidata point (docs/10,
  *Place dedup matches on names*), and a book's retellings are hidden after
  each of its contents is extracted (`dedup.hide_repeats`), so neither is a
  hand step any more.
- **Two books through the pipeline,** about $1: Wollstonecraft's 9 remaining
  Copenhagen windows (source 11, now rejected: an execution outside the city
  pinned on "Copenhagen", a ramparts walk, both hidden) and Brandes, *Levned*
  I (source 231, 49 windows, 4 kept: Christian IX blowing kisses from the
  Christiansborg balcony to cries of "Leve Grundloven!", Lehmann forcing the
  palace gate, the 1862 students greeted on Frue Plads, the gala at the
  theatre). A venue that is the city is no longer saved (`save_memories`).
  Runeberg's 1905 Danish spells it "Kjøbenhavn": "København" found 0 of 49.

The visible corpus went from 192 to 162 memories.

### A longer card, 2026-10-04

The founder asked for more text and richer memories (docs/10, *A card runs
as long as its source's details*). Both prompts' summary rule went from "2-3
sentences, 40-70 words and never more" to 60-180 words, earned: a lede that
would stop someone walking, the scene in order with every concrete detail the
source gives, then what came of it, and two paragraphs past about 90 words.
The archival quote may run to 40 words; the video one stays at 25, because a
longer line rarely survives the verbatim check against auto-captions.

`quality --compare --score` (new) also scores each kept summary on the walk
rubric and asks a thinking model what it says that its chunk doesn't
(`extract.unsupported`). 15 chunks a source type, one run unless noted:

| Source | Draws keeping something (15 chunks × 3) | Words | Walk score | Quotes | No added fact |
|---|---|---|---|---|---|
| Book, old | 13 of 45 | 57 | 6.7 | 5 of 7 | 6 of 7 |
| Book, new | 13 of 45 | 121 | 8.0 | 6 of 7 | 6 of 7 |
| Video, old | 20 of 45 | 45 | 6.2 | 9 of 13 | 12 of 13 |
| Video, new | 20 of 45 | 84 | 6.5 | 4 of 14 | 10 of 10 |
| Historisk Atlas, old | 14 kept, one run | 37 | 6.3 | 2 | 14 of 14 |
| Historisk Atlas, new | 14 kept, one run | 44 | 6.1 | 1 | 10 of 14 |

- **Length invites invention, so every kept memory is now checked.** Before
  the check, the longer summaries added things: "carved" for "decorated",
  "the city's finest", and once a Battle of Bosworth the guide never named.
  A prompt rule ("richness is the source's own details, never yours") halved
  that, not more. `extract.checked` asks the detector, and when it names
  claims, cuts exactly those and nothing else. Its first form rewrote the
  whole summary against the chunk: book summaries fell from 125 words to 74
  and one came back as "The story describes…". Both calls are stored, so a
  rerun is free. The "no added fact" column is that same detector on the
  final text, which makes it its own judge: read the summaries too.
- **"A life history is not a story" cost the best book memory.** The first
  candidate dropped Andersen jeered off the Royal Theatre's stage 0 of 3
  draws, against 2 of 3: a memoir chunk read as a life. Reworded to "a new
  detail of the same scene, not the years around it", it came back 2 of 3.
- **Truncation.** Four memories of 180 words overran the extractor's 2000
  tokens, and a cut reply is no JSON: Nygade Bio's four cinemas were lost.
  `extract_chunk_stored` now allows 8000.
- **Video quotes fell, 9 to 4.** Not yet understood (out of credit before a
  fix could be measured); the guess is that the longer summary spends the
  quotable line. Enrichment brings quotes of its own. TODO, *Video quotes
  after the longer card*.
- **The 107 video memories have no quote** because all of them were extracted
  on 2026-09-27, before the field existed (2026-10-01), not because the
  verbatim check fails.
- Historisk Atlas entries are a few lines, so its summaries barely grew: a
  small story stays small, as asked. Its "no added fact" fell on occupation
  context ("during the German occupation") the detector counts as added.

Read side by side, the new book cards are the change wanted: the Tuileries
drumroll that "within months would announce something far larger", the
Champs-Élysées carriages with their jockeys in green satin, the Kasino fire
told through.

A guessed `contrast_note` is no longer saved: 25 of 85 said "current use
unknown", "likely redeveloped" or "uncertain to me", though the prompt asks
for null. `extract.sure` drops a note that hedges.

- WHO: Use names ("Mark and Joe" not "the hosts")
- WHAT HAPPENED: Anecdotes, funny moments, mishaps
- THE VIBE: Emotions, humor, what made it memorable

### The check cut the lede, 2026-10-08

Memoir memories read as inventories ("Sorte Hane, the old soap-boiling house…",
a students' club room by room). The extractor was not the cause: its ledes were
hooks ("A schoolmaster escaped four watchmen here by being hauled up a wall").
`extract.unsupported` flagged the lede as added, because a lede compresses
("escaped", "here"), and the trim cut it, leaving the background first or a
fragment ("Saturday nights at the Students' Association rooms."). Measured on
the 37 summaries of 16 memoir windows (Bergsøe, Schorn, Zinck), check and trim
only:

| | Lede kept | Changed by trim | Fact claims |
|---|---|---|---|
| Old check | 27 of 37 | 22 | 24 |
| Check that lets a lede sum up the passage, and "here" | 29 of 37 | 17 | 19 |

Shipped. Four hooks came back (the wall, the tightrope walker, Borgerdydskolen,
Sorte Hane). One was lost: the elephant's "caused an uproar". The check is a
thinking call, so some of the five fewer fact claims are draw-to-draw noise, and
some may be real catches given up. Also tried, and none of the three shipped:

- A trim rule to cut the whole sentence rather than leave it broken. It changed
  nothing: the students' club stayed a fragment. Since 2026-10-09
  `extract.broken` keeps the untrimmed summary when a trimmed sentence starts
  mid-clause or newly ends on "for Roat's." or "the."; a verbless fragment
  like the club's still passes.
- A summary prompt putting the event first and banning inventories. It was 10%
  shorter (134 to 121 words) but its ledes went chronological ("In 1827 the rope
  dancer Roat came to Copenhagen").
- A walk-score sink for inventories. It moved memoir scores by about 1 point
  either way, the judge's own noise, and lost on the 219 labels: AUC 0.717 to
  0.687.

Memories already stored keep their trimmed summaries.

### About the spot, 2026-10-09

A memoir card could still be told anywhere. Example: the quartz mill card was
"mumbo jumbo" (the founder): it never said the mill was in the porcelain
factory's yard on Købmagergade, nor what a quartz mill was. Its pin was a
guess, on Nørrebro. Three causes:
- the prompt treated the place as a setting;
- a book window had no brief;
- the model placed the pin.

**Shipped as an interim fix** (`HISTORICAL_SYSTEM_PROMPT`, `book_brief`):
- The spot is the subject. Open on where the reader stands and what was there,
  close on what of it they can still see.
- Keep the details that make the scene, not rooms, fittings or owners in turn.
- Gloss old words. Name a person only when the story needs it.
- `spot_test` fails a place neither the text nor the brief locates.
- A book window gets a brief made from the book's first three windows,
  `<book_brief>`, built like `video_brief`.

Measured on the 16 memoir windows with extraction and check, no judge: 39
memories against 18 stored, 132 words against 142. The extra memories are
there because no judge ran. Results:
- Ledes open on the spot (Kongens Nytorv, Store Larsbjørnstræde).
- The tightrope walker moved from Amager Fælled to Rosenborg.
- Rundetårn no longer puts Bergsøe there in 1807.
- New problems:
  - "This was…" opened most cards.
  - Postgården and Sorte Hane stayed inventories.
  - Bergsøe's brief is genealogy, because his first pages are.

**Research** (three agents; this adds to *Research, 2026-10-02*):
- **No product extracts place stories from books automatically.** VoiceMap,
  Clio, Detour, Autio, Atlas Obscura and Hidden Copenhagen all have writers
  and an editor.
- **The nearest automated work hit our failures:**
  - Edinburgh's Palimpsest/LitLong
    ([Loxley et al. 2017](https://www.storre.stir.ac.uk/bitstream/1893/28517/1/DSH_article_finalrevisions.pdf)):
    its worst false hits were family histories, registers and catalogues,
    which are dense with place names. Ranking precision was MAP 0.13, then
    0.17 after feedback, and scholars still curated.
  - Stanford Lit Lab's London project
    ([Pamphlet 13](https://litlab.stanford.edu/LiteraryLabPamphlet13.pdf)):
    only about half of place mentions are the scene of the action.
- **Interpretation craft.** Tilden, Ham's TORE, NPS, and Te Papa's
  [label guide](https://www.tepapa.govt.nz/assets/76067/1687925811-28-writing-effective-interpretive-text.pdf):
  - one theme per text, a sentence with a point;
  - tie what can be seen to what happened there;
  - "a chronology or a list of facts" is the named failure;
  - gloss jargon.
- **Audio tours.** VoiceMap's
  [writing guide](https://docs.voicemap.me/tour-publishers/writing-scripts-that-make-listeners-feel-something/):
  "tell the story of just one", at most two names.
- **Pipelines:**
  - Pick the story apart from writing it
    ([StorySeeker](https://arxiv.org/abs/2311.09675)).
  - Index the whole source first
    ([contextual retrieval](https://www.anthropic.com/news/contextual-retrieval)).
  - Resolve the place before writing.
  - Teach style with varied examples rather than rules
    ([multishot](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/multishot-prompting)):
    a rule becomes a template, as "This was…" did.

**A scene-first pipeline, trialled and not shipped** (about $10, nothing
saved). It has four steps:
1. **Index.** One call reads the whole book and writes people with their roles
   and places with what they were and where.
2. **Find scenes.** Per window, a scene finder writes no prose. It classifies
   each candidate by place use (scene, mention, discourse), shape (scene,
   list, lineage, chronicle, description), turn, and a theme of at most 15
   words. Code keeps scene, scene, turn, theme. It names the spot as today's
   map does.
3. **Write.** The geocoder places the spot. A short writer prompt with four
   varied example cards writes from the scene, the spot and the people.
4. **Check.** Today's check and trim.

The comparison was against the stored cards on 24 windows: the 16 above plus 8
Grandjean and Gottschalksen windows that already had memories. The pairwise
judge ran in both orders, and only verdicts that agree count. The first run
lost 4 to 17, because the index's places were prose and covered only 15–32 per
book, so 47 good scenes found no spot. With the finder naming the spot:

| | Stored | Scene-first |
|---|---|---|
| Cards | 30 | 52 |
| Mean words | 137 | 118 |
| Windows won (both orders) | 6 | 10 (8 split) |
| Candidates dropped as description, chronicle, lineage or no turn | - | 100 |

- **The writing is better.** The quartz mill card now says the factory stood
  there until 1885, with its yard against Trinitatis churchyard, and the ghost
  turns out to be a drying sheet.
- **It finds stories the stored cards missed:** the bear cub on the quay, the
  cat through the plate glass, the Wildersgade mud town, Moltke at Tivoli.
- **It loses on:**
  - two cards for one anecdote, so it needs one card per scene;
  - repeated openers ("The old Royal…" ×6), which a first-three-words check
    would catch;
  - two windows it left empty (Zinck's theatre debut, the elephant);
  - a trim that left a card garbled.

82 cards, shuffled and blind, wait for the founder's labels before
it ships (TODO.md, *Scene-first extraction*).

### Scene-first, before it ships, 2026-10-09

The trial now lives in `pipeline/scenes.py` (`python -m pipeline.scenes <id>...`,
bills only the windows named; shipped 2026-10-10, below). Three of the four items before it
ships, rerun on the five windows they came from (3898, 3900, 3903, 4000, 4001)
for about $1.10 at Sonnet's list price, mostly the thinking check:

- **One card per scene.** The finder prompt now says one anecdote is one
  candidate, from where it starts to its payoff. Zinck's fall on Kongens
  Nytorv and his brother's engagement came back as one card that reaches the
  debut; the rope-dancer and "peas and pork", two stories at one house, stayed
  two. Not solved: a story's coda can still leak into a neighbour's card
  (Herlufsholm's beech climb ends on the carving that has its own card).
- **The first three words.** `opening_fault` rejects a stock opening ("This…",
  "Here…", "The walker…", "Nothing is left…", a date first) and one that
  already opens another card in the run; the writer gets one more draw told
  why. 4 of 15 cards were redrawn, and each came back opening on the person or
  the moment ("A rope-dancer named Roat came…", "Otto Zinck was a small boy,
  crying at an open window…"). "The walker is on Østergade…" was added after it
  passed. Not caught: near-repeats such as "Classens
  Have is…" and "Classens Have lies…", five cards on one spot from one window.
- **The two empty windows were the pipeline's fault, three times over:**
  - *Theatre fall (3903) and the elephant's window (4000):* the finder's list
    stopped after its first candidate, covering 7% and 3% of the passage
    (every other window reached 53-99%). In 3903 the reply's last string
    even held `}},{"`. A list that ends before half the passage is now asked
    again for the rest. 4000 then gave six scenes, Kaspar the donkey torn in
    two on stage among them.
  - *The theatre fall:* its place words were "det nye kongelige Teater", and
    the scan puts a running head and page number between "nye" and
    "kongelige", so the exact-copy test dropped it. `copied` lets up to 80
    characters stand between the words. The card is back: the fall through the
    floor of the unfinished theatre, umbrella in hand.
  - *The elephant:* its turn (it eats the boy's cap and bread) is on the next
    window's first page; windows don't overlap. The finder now gets the last
    1,500 characters of the window before as `<before>`, and a scene belongs
    to the window it ends in. 4001 now tells it whole, from the night walks
    round the Horse to the new cap on Østergade.

Seen on the way: the check's trim broke a sentence ("to raise money for
Roat's."), now guarded in code (*The check cut the lede*); the finder places
Herlufsholm and Lolland scenes, outside Copenhagen. Book scans kept their running heads and page numbers;
since 2026-10-09 `crawler.gutenberg.unpaged` drops them at ingest, and
`copied` keeps its slack for the windows ingested before.

**The founder's first labels** (20 of the 82 blind cards,
`docs/labels/scene-first-blind.md`): stored 7 of 8 glad to know, scene-first 9
of 12. Nearly every note was the same: *who is this?* The note was written for
Grandjean, Zinck, Phister, Dahl, Thorvaldsen and the pastor, and for words
("humbug", "quay"). Two *no* cards only happened to take place where they are
pinned (a flat, a shop). So:
- The writer introduces everyone named, the author included, from the index's
  roles. It uses words a reader with school English knows.
- The finder has a fourth `place_use`, `setting`: a home, shop or office where
  the same moment could have happened in any other. Code drops it.

Rerun on the 11 windows behind the labelled cards, about $2:
- Every card now says who people are: "Phister, the leading comic actor",
  "Axel Grandjean, the composer and conductor", "Pastor Visby, the chaplain of
  the prison and workhouse", "Otto Zinck, three years old". "Humbug" became
  "a farce".
- `setting` dropped 18 candidates, among them both *no* cards (the imaginary
  guests in a Nørregade flat, the Holberg portrait in a Nygade shop) and a
  classroom.
- **Still wrong:**
  - The trim damages cards mid-sentence, where the end-of-sentence guard
    can't see it: "Retelling it later," ends one card; "his father and two
    Royal Theatre colleagues, Rosenkilde, put on…"; "played Peter the Great
    himself, as Catharina".
  - One window gives five cards about one week of November 1863, two of them
    the same night in Amaliegade.
  - A new stock opening has replaced "This was": "Kongens Nytorv is where…",
    "Tivoli is where…", "Børsbroen was where…".

**A flagged card is written again, not cut** (`scenes.faithful`). When the
check names a claim, the writer draws the card again, told what the passage
does not say. Only what the second draw still adds is trimmed. Same 11
windows, about $1:
- 25 cards, 14 flagged, all 14 rewritten. 12 rewrites still carried a claim
  and were trimmed: the thinking check names something new on each draw.
- Bournonville and Roat came back whole ("Telling the story later, he added:
  'Yes, I was saddened!'"; "The actor Rosenkilde and Zinck's father then put
  on a benefit performance").
- Two cards are still damaged:
  - "He played Peter the Great, both in crowns and ermine cloaks": the check
    called "his wife" unsupported twice, and the trim cut it.
  - "and 15 November 1863, a wild crowd gathered here".

**Round 3, about $3.** Three changes:
- One event told at several places is one candidate.
- "<Place> is/was where…" counts as a stock opening.
- A second draw that still adds a fact is dropped.

Result: 21 cards, from 25.
- No card is cut mid-sentence. "Peter the Great… in a crown and ermine
  robes" is whole.
- The November 1863 week gives four distinct moments, not five with a repeat.
- Seven cards were dropped, and several were among the best: the theatre
  debut, the fire watched from the Børs, the mother's grave, the foyer the
  night the king died. The claims they lost on were nitpicks: "sixteen",
  "volunteer", "had been crying in secret". The thinking check names something
  new on each draw, so one rewrite is not enough.
- The colour trim still produced "Telling the story later, he added a line."

So `faithful` now never cuts. The writer draws up to `REWRITES` (2) more
times, told every claim named so far. A card is dropped only if a fact is
still added after that. A card with only colour left is kept as written.

**Round 4, about $2:**
- 24 cards, 23 rewrites, 4 dropped. No sentence is broken.
- Back whole: the Toby debut (now with its payoff, the angry letter and the
  release), the fire seen from Børsen, and the foyer the night the king died.
- Still dropped: the mother's grave ("for the first time the boy understood
  that she was dead", "eleven-year-old"), and two 1863 cards.
- **Open:**
  - A kept flourish can be a generalisation the source doesn't make
    ("Authors rarely get a second chance").
  - A rewrite's opening is not checked, so "This was…", "On the evening of…"
    and "Børsen is where…" got back in: 5 of 24.
  - The Nygade shop card, dropped as `setting` in round 2, came back.

**Shipped, 2026-10-10** (docs/10, *Scene-first is the book path*): `--save`
runs `after_save`, openings count per book, a rewrite's opening is checked,
and a scene outside the launch area is dropped before it is written. Same-event
cards and leaked payoffs are left to dedup.

### Yield by genre, 2026-10-07

The 412 visible memories, grouped by source. A source's genre predicts its
good (6+) share better than the prompt does. Caveat: the memoirs, Københavnerliv
and the plaques were all scored before 2026-10-05 (the old, looser scale) and
the institutions all after, so the gap is overstated; the order is the claim,
not the size. The next memoir trial checks it on the new scale:

| Genre | Sources | Good |
|---|---|---|
| First-person memoir | Andersen, Leonora Christina, Carl Møller, Brandes, Oehlenschläger | ~80% |
| People telling their own places | Københavnerliv 68%, Københavnerglimt 54% | ~58% |
| Plaques, researched | OSM plaques (5) | 5 of 5 |
| Local-history society | Nørrebro 75%, Valby 25% | mixed |
| An institution about itself | Tivoli 0, Parken 0, Magasinet KBH 0, K.B. Hallen 20, Noma 25 | ~10% |
| Encyclopedic | Wikipedia, modern Copenhagen (57) | 14% |

- Tags agree. *personal* (6.8), *comedy* (6.9), *family* (6.5) and *strange*
  (6.4) score high; *music* (4.2), *work* (4.8) and *sport* (5.0), the venue
  sites' themes, score low.
- Undated memories average 6.0 and year-dated ones 4.5: stories carry no
  date, encyclopedias always do.
- The day's institutional trials spent about $10 for 3 good memories.
  Københavnerglimt made 27 for about $27.
- The 200 good are on two scales. Before 2026-10-05, 111 of 169 (66%) were
  good; since then, 89 of 245 (36%). Plan by the new rate.
- An archival source can leak its own voice into the summary: "the manuscript
  gives a rare glimpse", "later tellings added", "the museum recommends". It
  is rare: 4 of the 412 visible, all from Københavns Museum (260), LGBT+
  Danmark (264) and Rundetårn (269). A prompt rule against it was measured
  with `quality --compare` on 20 press chunks: 0 hits before, 1 after, so it
  didn't ship. `quality` counts it as *talks about the source*, and the fix
  is the source: pick its story pages, not its reports.
- 60 visible memories score under 4. A walk no longer stops at them (docs/10,
  *A dull story is no stop*).
- The map is thin. 54 occupied 1 km cells, the densest with 94 memories, the
  median with 3. The skills now weigh empty cells and genre when choosing a
  source.

### Road to 1,000 (Copenhagen)

The goal is 1,000 good memories in the launch bbox. Good means visible and
`walk_score >= 6` (7 until 2026-10-07: docs/10, *Famous people at a spot, and
good is 6*). `.claude/skills/make-memories` runs one source per pass and adds a
line here. Started 2026-10-05 at 74 good out of 169 visible. On 2026-10-07,
403 visible: 116 at 7 or more, 197 at 6 or more. Rows above that date count
"Good" at 7.

| Date | Source | Items | Memories | Good | Mean score | $ |
|---|---|---|---|---|---|---|
| 2026-10-05 | Historisk Atlas (10), ids 176-217 | 40 | 10 | 0 | 4.2 | ~5.60 |
| 2026-10-05 | Wikipedia, modern Copenhagen (245), trial | 5 | 7 | 0 (old scale) | 4.3 | ~1.70 |
| 2026-10-05 | Wikipedia, modern Copenhagen (245), rest; new scorer | 67 | 54 | 4 | 4.3 | ~9 (13.50 at full price) |
| 2026-10-05 | Trials: Stolpersteine (246), Bryggebladet (247), Nørrebro Lokalhistoriske Forening (248), Christianshavneren (250) | 20 (5 each) | 12 (2/3/4/3) | 3 (1/0/2/0) | 5.3 | ~3-5, est. |
| 2026-10-06 | Københavnerglimt (3), trial, ids 617-621 | 5 | 28 | 7 | 5.5 | ~8, est. |
| 2026-10-07 | Københavnerglimt (3), rest, ids 622-640 (633, Bakken, stuck on cut replies) | 16 | 101 | 27 | 5.6 | ~27, est. |
| 2026-10-07 | Noma (256, 22 Copenhagen posts), Tivoli (257), Distortion (258); no trial | 25 | 14 | 2 | 4.6 | ~5, est. |
| 2026-10-07 | Trials, most story-like chunks: Magasinet KBH (254), NABO Humleby (252) | 10 (5 each) | 9 (8/1) | 0 | 3.8 | ~2-4, est. |
| 2026-10-07 | Trials, first window each: K.B. Hallen (261), Copenhagen Pride (263), Jazz Festival history (265), Jazzhus Montmartre (266), Parken (267), Fiskebaren (268) | 6 | 10 (5/1/0/1/2/1) | 0 | 4.3 (best: Lars Ulrich at Deep Purple, Montmartre, 6) | ~3, est. |
| 2026-10-07 | Trials, public-domain memoirs, first 5 windows each: Gottschalksen (281), Bang vol. 6 (282), Grandjean (283), Egan (284) | 20 | 6 (1/0/4/1) | 5 | 6.8 (new scale; Battle of Fælleden 1872 and a bear cub on Nyhavn, 8) | ~5-7, est. |
| 2026-10-08 | Grandjean (283) and Gottschalksen (281), the rest of both books | 46 | 7 (5/1 kept, 1 hidden as a retelling) | 5 | 7.3 (Moltke ends Balduin Dahl at Tivoli, 9) | ~5-8, est. |
| 2026-10-08 | Trials, channels once captions came back: Gotha & Petersen walks (192, 2), Københavns Museum Nørrebro oral history (273, 2), Paul-Erik Lind's Sydhavnen (277, 1), *Ungeren indefra* (278, 1); Olsen-banden (274) has captions disabled | 6 | 11 (8/2/1/0) | 1 | 4.0 (guided walks read as lectures, 3-4; Nørrebro's own people 5 each; Mariakirken, 6) | ~2-3, est. |
| 2026-10-08 | Trials, Copenhagen-only memoirs, 5 densest windows each: Bergsøe (285), Schorn (286), Sødring (287), Zinck (288), Foersom (289) | 25 | 10 (6/1/0/3/0) | 10 | 7.4 (Svenningsen hoisted up a Store Larsbjørnstræde wall away from the watch, 9; 1807 night on Rundetårn, 8) | ~3-5, est. |
| 2026-10-08 | Bergsøe (285) and Zinck (288), the rest of both books | 87 | 11 (6/5) | 9 | 7.0 (a ghost in the quartz mill that was a drying sheet, 9; but an inventory of the students' club scored 7) | ~10-15, est. |
