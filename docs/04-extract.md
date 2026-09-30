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
| `country` | ISO 3166 two-letter code. Routes to national geocoders (DAWA for `DK`) |
| `address` | Street and number if the source names one, in today's spelling. With `venue`, what the geocoders place; `lat`/`lng` is the fallback ([why](10-decisions.md#the-llm-names-the-place-free-geocoders-place-it)) |
| `lat` | Latitude, estimated by the model. A memory without coordinates is filtered out of every API query. |
| `lng` | Longitude, same. |
| `timestamp_start` | When place is first mentioned (from [timestamp] markers) |
| `summary` | 2-4 sentences capturing the story - who, what happened, the vibe. Conversational, not a summary in the report sense. |
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

Measured from the console balance, since the logs carry no output tokens
(TODO.md, Friction). Sonnet 5 extracts; Haiku screening is cents.

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

Flags: `out` outside Copenhagen, `pin` a street, district or shared centroid,
`p1000` a named site at 1000 m, `wrong` the wrong place, `dup` a near-duplicate,
`ctx` a name or speaker never introduced, `desc` no incident, `adv` present-day
promotion, `priv` a private person's death, health or crime, `hall` a likely
factual error, `stale` relative time, `obsc` only for specialists, `german` a
German place name left in.

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

**None of it has been run against real credits** (the account balance is empty),
so the numbers above are still the current state.

- WHO: Use names ("Mark and Joe" not "the hosts")
- WHAT HAPPENED: Anecdotes, funny moments, mishaps
- THE VIBE: Emotions, humor, what made it memorable
