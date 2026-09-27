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

## Memory quality
The summary is the product: somebody standing on the spot, on a phone, outdoors.
Measure before and after any prompt change — extraction costs money and you get
one shot:

```bash
python -m pipeline.quality
python -m pipeline.quality --compare candidate.txt   # same 10 chunks, both prompts, side by side
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

**None of it has been run against real credits** (the account balance is empty),
so the numbers above are still the current state.

- WHO: Use names ("Mark and Joe" not "the hosts")
- WHAT HAPPENED: Anecdotes, funny moments, mishaps
- THE VIBE: Emotions, humor, what made it memorable
