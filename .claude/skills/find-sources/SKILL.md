---
name: find-sources
description: Find, vet and trial new sources of place memories for Memory Lane (podcasts, press, books, archives, open data). Use when asked to find more memories, new sources, or to check whether a feed, book, archive or channel is worth ingesting.
---

# Find sources

A source is worth it when its stories happen *at a spot a walker can stand on*,
we may use it, and it yields memories that score on the walk rubric. This is
the funnel, in order. Each step is cheap until the one marked **bills**.

Read first: `docs/10-decisions.md` → *The sources' legal footing* (the table),
*Sources are a Protocol and a registry*, *Sources are rows with a status*.

## 1. Research candidates (free)

Fan out parallel agents, one per kind, on primary sources only: the feed
itself, the catalogue page, the ToS page. Not listicles. Ask each for exact
locators and evidence.

| Kind | Plug-in (`crawler/`) | Locator (`<key>:<query>`) | What makes one good |
|---|---|---|---|
| Plaques, memorials | `plaques` | `plaques:<s,w,n,e>` | Already names its spot; exact pin |
| Film and TV shot here | `filming` | `filming:<s,w,n,e>` | Wikidata P915 to a spot, not a city |
| Wikipedia places | `wikipedia` | `wikipedia:<lang> <lat>,<lng> <metres>` or `wikipedia:<lang> category:<A>|<B>` | History sections with incidents; categories beat a radius, which drags in stubs and the citywide article |
| Press feed | `press` | `press:<feed url>` | Only with the outlet's agreement: every Copenhagen outlet reserves TDM (§11b) |
| Podcast feed | `podcast` | `podcast:<feed url>` | Items carry `<podcast:transcript>` (no Copenhagen show did, 2026-10-04); no audio is transcribed |
| Public-domain book | `gutenberg`, `runeberg` | `gutenberg:<id> <word>`, `runeberg:<key> <word>` | Memoir of a city life, author dead 70+ years |
| Internet Archive book | `archive` | `archive:<item id> <word>` | A walk book by street or house, author dead 70+ years; roman type, not Fraktur |
| Old newspapers | `kb-aviser` | `kb-aviser:<query>` | Over 140 years old |
| Historisk Atlas | `historisk-atlas` | `historisk-atlas:<title word>` | CC or PD licence only |
| YouTube channel | `pipeline.sources discover` | channel URL | Only with written permission (`docs/permission-request.md`) |

A kind with no plug-in is one file in `crawler/` with a class that fits
`Source`, plus one line in `crawler.sources.SOURCES`, and an offline parser
test in `tests/test_crawler_sources.py`. A source with its own coordinates puts
them in the record's text ("X places this at lat, lng"), as `historisk_atlas`
does, so the pin can use them.

## 2. Legal check (free)

Find the kind's row in the legal table. If there is none, write it **before**
ingesting: the licence or ToS clause, quoted with its URL, and what it takes.
Hard stops: no reuse or TDM opt-out in the ToS, non-commercial only, a
private person's health, politics or crime (GDPR Art 9), and anything needing
a login, a paywall bypass or a proxy. Press and podcast text is forgotten once
extracted (`pipeline.transcripts.forget`); we keep facts in our own words and
a link.

## 3. Register and fetch a sample (free)

```bash
venv/bin/python -m pipeline.sources add text '<key>:<query>' "<credit name>" --licence "<licence>" --note "<why>"
venv/bin/python -m pipeline.ingest --source <key> --query '<query>' --limit 5 --bbox 55.60,12.45,55.74,12.66
```

Read two or three ingested texts yourself (`transcripts.full_text`). If they
don't name places a walker can stand on, `set <id> rejected --note` and stop.

## 4. Screen (a few cents, Haiku)

```bash
venv/bin/python -m pipeline.sources screen <id> --sample 3
```

Under about 0.3 pass rate: reject with a note.

## 5. Trial (**bills**: Sonnet extraction, check, judge, enrichment)

```bash
venv/bin/python -m pipeline.sources set <id> trial
venv/bin/python -m pipeline.enqueue --video <content_id>   # one item; never pipeline.extract
venv/bin/python -m pipeline.worker --burst
```

Before enqueueing, check that it isn't already queued or extracted
(`content.memories_extracted`, the queue). After it runs, run the duplicate
summary query, then read every new memory and its `enrichment`.

## 6. Decide and record

- Yield: memories per item, mean `walk_score`, how many survived the check.
  Keep a source whose memories average 7 or more and that names spots.
- `set <id> active` or `rejected`, with `--note` saying why.
- Log the numbers in `docs/04-extract.md` or `docs/02-ingest.md`, and the
  legal row in `docs/10-decisions.md`.

## Don't

- Run `python -m pipeline.extract`: it bills every pending item.
- Ingest a whole feed or the 4,000-article Wikipedia set before a 5-item trial.
- Add a source whose stories are only *set* in a place: the judge drops them,
  and you pay for that.
