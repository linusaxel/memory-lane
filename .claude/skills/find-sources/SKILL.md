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

## 0. Already searched (read before researching)

Re-check only what is marked open. Dated, so a stale entry can be re-tried.

**Without permission (2026-10-05)** is allowed for sources that don't opt
out, as long as nothing circumvents a block: docs/10, *Recent sources without permission*.

**By era (2026-10-05).** The free sources stop at about 1945. Living memory,
and above all the 2010s to now, comes only from permission or from people in
the app. Don't search the open web for free recent stories again.

| Era | Where it is | State |
|---|---|---|
| 2010s-now | Wikidata events in the bbox with P585 ≥ 2010: about 10 (Hotel Jørgensen 2010, the 2015 shootings, Field's 2022, Børsen 2024). Mostly grim, so they fail "glad to know" | Not worth a source |
| 2010s-now | Nonprofit local papers as PDFs, with no TDM reservation: Bryggebladet (redaktion@bryggebladet.dk, about 21 issues a year 2003-26), Christianshavneren (christianshavneren@beboerhus.dk, 2011-17 plus web), Havnefronten (red@havne-fronten.dk, since 2020, mostly openings) | Registered (`pdfs:` index pages): Bryggebladet 247 from 2019 (the archive page lists only 2019 onwards; news plus ad pages), Christianshavneren 250 (homepage PDFs, mostly event listings), Nørrebro yearbooks 248 from 2010 (recent issues write about older history). Havnefronten 249 was rejected: its feed is council news through a tracker. Untrialled |
| 2010s-now | Bar stories: VLTV's *De Brune Værtshuse* on YouTube (vltv@hotmail.com, auto-captions); the podcasts *Sidste Omgang* (86 episodes, one bar each, Instagram @sidste.omgang) and *Barvox* (info@barvox.com); the book *Stamsteder* (220 pubs, 2021, print only) | VLTV is registered as source 251: 10 bar videos ingested (two others are gone), with captions waiting on YouTube's IP block. The podcasts have no transcripts, and we don't transcribe audio |
| 1950-2000 | Local-history society yearbooks: Nørrebro (24 PDFs 2000-23, about 80-100 good), Sydhavnen (26 articles), SLAK for the other 8 | Email drafted in `docs/permission-request.md`, not sent |
| 1940-45 | Stolpersteine, `stolpersteine:Liste der Stolpersteine im Großraum Kopenhagen` (source 246, 46 addresses) | Ingested, not screened |
| 1860-1919 | Public-domain memoirs: Gottschalksen `archive:engladmusikantsd00gott` (densest), Bang `runeberg:bang/6 København`, Grandjean `archive:spredtemindergen00gran`, Egan `gutenberg:36412 Copenhagen` | Not registered |

**Dead ends.** Don't retry these without new evidence.
- **Encyclopedic Wikipedia.** The en category set (venues, riots, crimes,
  clubs) gave 4 good from 67 items (source 245). Danish Wikipedia's 2,783
  geotagged articles read the same, with a rare gem such as Elmegade 23 or
  Cafe Intime.
- **Historisk Atlas** gives title and intro only, with no licence in the
  public JSON. The sabotage set scored 0 good.
- **Records that are labels, not stories:** Europeana's listed buildings (CC0,
  boilerplate), the Kommune's open data (`monumenter` has no text), Wikinews,
  Wikivoyage, OpenHistoricalMap, and one-line Wikidata descriptions.
- **No usable text:** Nationalmuseet, modstand.natmus.dk, Arbejdermuseet and
  the Folklore Archives (no open licence or only on site); Københavns Museum
  podcasts (no transcripts).
- **No Copenhagen memoir as free text:** Nexø's *Erindringer*, Pontoppidan,
  Michaëlis, J.V. Jensen, Wied, Drachmann and Aakjær. Thit Jensen and
  Johannes Jørgensen are still in copyright.
- **District weeklies** (Vesterbro Bladet, Østerbro Avis, Valby Bladet,
  Amager Bladet/amagerliv, City Avisen) are Jysk Fynske Medier.
  lokalavisen.dk redirects to dinavis.dk, which reserves TDM and blocks
  anthropic-ai. They're closed, as the press row says.
- **Collections that turned out to be pre-2010 or not stories:** Københavns
  Museum's and Københavns Biblioteker's podcasts (older history), *Gang i
  gaden* (centuries ago, retold), the corona collections (objects, or for
  researchers only), and Kanal København (shut 2009).
- **Unchecked:** Copenhagen history accounts on Instagram, which search
  doesn't index. Look by hand.
- **Local-history websites with no stories to read:** chrarkiv.dk (photos),
  Islands Brygge (books for sale), Kend Din By (film), erindringer.dk (dead).

**Lessons.**
- A source's last items can be off-topic: Københavnerliv's backlog ended in
  film chats and festivals. Read the pending titles before trusting `expected`.
- Ingest everything when a source is small, and trial the richest items, not
  the first five.

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
