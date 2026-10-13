---
name: make-memories
description: Resume making Memory Lane memories toward the goal of 30 good ones in every km near Copenhagen's centre. One pass per kick-off - progress, pick the best source, ask, batch-extract, check, log. Use when asked to make, resume or continue memory creation, or to say how far we are from the goal.
---

# Make memories

**Goal: 30 good memories in each of the 51 km cells within 4 km of
Rådhuspladsen, 1,530 in all** (docs/10, *Thirty good in every kilometre near
the centre*). Good means visible, not a user's, and `walk_score >= 6`. A
memory past 30 in its cell doesn't count toward the goal. The database is the state: every
pass starts by counting, so there is nothing to resume by hand.
Scores from 2026-10-05 on are stricter (docs/10, *The walk score asks one
question*), so a source's old good-per-item overstates its yield now.
A 6 is not yet glad-to-know: on 2026-10-13 a read of every card found a
third dull, many of them at 5-6 (docs/04, *Fun read*). Read the cards, not
just the count.

One pass, one source. Every step is free except the one marked **bills**, and
that one waits for a yes.

All SQL runs as `docker exec memory-lane-db-1 psql -U memorylane -d memorylane -c "<sql>"`.

## 0. Where are we (free)

```sql
SELECT count(*) FILTER (WHERE NOT m.hidden) visible,
       count(*) FILTER (WHERE NOT m.hidden AND m.walk_score >= 6) good,
       count(*) FILTER (WHERE NOT m.hidden AND m.walk_score IS NULL) unscored
FROM memories m JOIN places p ON p.id = m.place_id
WHERE m.user_id IS NULL
  AND ST_Y(p.coordinates::geometry) BETWEEN 55.60 AND 55.74
  AND ST_X(p.coordinates::geometry) BETWEEN 12.45 AND 12.66;
```

Coverage, the goal: `toward_goal` out of `goal`.

```sql
WITH hall AS (SELECT ST_Transform(ST_SetSRID(ST_MakePoint(12.5683, 55.6761), 4326), 25832) g),
cells AS (
  SELECT x, y FROM hall,
    generate_series(floor(ST_X(g) / 1000)::int - 4, floor(ST_X(g) / 1000)::int + 4) x,
    generate_series(floor(ST_Y(g) / 1000)::int - 4, floor(ST_Y(g) / 1000)::int + 4) y
  WHERE ST_Distance(ST_SetSRID(ST_MakePoint(x * 1000 + 500, y * 1000 + 500), 25832), g) <= 4000),
good AS (
  SELECT floor(ST_X(t) / 1000)::int x, floor(ST_Y(t) / 1000)::int y, count(*) n
  FROM memories m JOIN places p ON p.id = m.place_id,
    LATERAL ST_Transform(p.coordinates::geometry, 25832) t
  WHERE m.user_id IS NULL AND NOT m.hidden AND m.walk_score >= 6
  GROUP BY 1, 2)
SELECT count(*) cells,
       count(*) FILTER (WHERE n >= 30) full_cells,
       count(*) FILTER (WHERE n IS NULL) empty_cells,
       sum(least(coalesce(n, 0), 30)) toward_goal,
       30 * count(*) goal
FROM cells LEFT JOIN good USING (x, y);
```

Swap the last `SELECT` for `SELECT x, y, coalesce(n, 0) FROM cells LEFT JOIN
good USING (x, y) ORDER BY 3` to list the emptiest cells.

Unscored memories get `venv/bin/python -m pipeline.walk_score --all`, which bills
pennies. Ask first.

## 1. Nothing half-done (free)

```bash
pgrep -fl "pipeline.(batch|worker)"
```

If a batch is still running, report and stop. **Never kill one mid-poll**: the
results it is waiting on are paid for, and they are lost if you kill it, so the
next run pays for them again. Never start a second batch.

## 2. Pick one source (free)

Expected haul is good memories per extracted item × items pending:

```sql
WITH done AS (
  SELECT c.source_id, count(DISTINCT c.id) items,
         count(m.id) FILTER (WHERE NOT m.hidden AND m.walk_score >= 6) good
  FROM content c LEFT JOIN memories m ON m.content_id = c.id AND m.user_id IS NULL
  WHERE c.memories_extracted GROUP BY 1),
pending AS (
  SELECT c.source_id, count(*) n
  FROM content c JOIN transcripts t ON t.content_id = c.id
  WHERE NOT c.memories_extracted AND NOT c.extraction_failed GROUP BY 1)
SELECT s.id, s.name, s.status, p.n pending, d.items done, d.good,
       round(coalesce(d.good::numeric / nullif(d.items, 0), 0) * p.n) expected
FROM pending p JOIN sources s ON s.id = p.source_id LEFT JOIN done d ON d.source_id = s.id
WHERE s.status NOT IN ('candidate', 'rejected')
ORDER BY expected DESC, pending DESC;
```

- Take the top row, unless it is out of the launch area: Tuesdays with Stories
  is US comedy, and the bbox drops every memory it yields.
- **Trial the next 5 pending ids before any bigger batch**, of any source:
  run `batch --content <5 ids>` with those five ids. `expected` is the
  source's past, not its next items: Historisk Atlas showed 90 expected, and
  its next 40 were thin records with no good memory.
- With no track record, genre is the prior (find-sources step 1): memoirs and
  people telling their own places first, an institution about itself last.
- **Coverage decides between near-equals.** A source's worth is its good
  memories that land in ring cells still under 30. One in a full cell, or
  outside the 4 km ring, doesn't move the goal. Count where its places would
  land against step 0's cell list: a 6 in an empty cell beats the fortieth in
  Indre By. A one-venue
  source gives a walk at most one stop there, whatever it yields.
- **One teller, a few stops.** At most 15 good memories per author, across
  all their books (the source name starts with the author). A walk that is
  every second stop Bergsøe is one man's diary, and a teller the walker may
  have heard of (Andersen, Oehlenschläger, Blixen) beats an obscure one at
  the same yield. Bergsøe reached 25 on 2026-10-10: no more of his books.
- **One theme, a few stops.** At most 30 good memories per theme or era:
  WW2 (1939-45) stood at 30 on 2026-10-10, so no more occupation sources,
  however well they score (Frihedsmuseet's pictures did). Count with
  `extract(year FROM happened_at)`. Recent (1960-now) comes first: it had 13 (docs/10, *No teller or theme
  dominates*).
- If a source's done items average under 7, run
  `venv/bin/python -m pipeline.sources set <id> paused --note "<why>"` and skip it.

## 3. Thin backlog: find new sources

If the best `expected` is under about 50, or nothing is pending, follow
`.claude/skills/find-sources/SKILL.md` steps 1-4 instead. Its step 5 trial
comes back through step 4 here: ask first, and batch rather than worker.

## 4. Ask, then batch (**bills**)

```bash
venv/bin/python -m pipeline.batch --source "<exact name>"   # dry: counts pending
```

Tell the user the items, the expected good memories, and the estimated cost.
Use the source's own $/memory from `docs/04-extract.md` § Road to coverage if a
run has been logged; otherwise use about $0.05 per memory extracted in a batch
(measured 2026-10-11 from the Batches API usage, research paused), or about
$0.15 per good one. The $ logged before 2026-10-11 were guessed at $0.25 a memory. Ask with AskUserQuestion. On a yes, start it
with `run_in_background` and wait for the notification. Don't poll.

```bash
venv/bin/python -m pipeline.batch --source "<exact name>" --run
```

A book goes scene-first with fact sheets on its own; add `--scenes` for any
other text (Wikipedia, PDFs, pages), so its cards can be written again from
their sheets with `batch --render <source id> --run`.

A batch takes minutes to hours, and each pass polls every 30 s. If it exits
with "stored nothing", stop and report. Don't retry.

## 5. Check what it made (free)

```bash
venv/bin/python -m pipeline.dedup --memories --source <id>   # dry run: retellings
venv/bin/python -m pipeline.quality --faults --source <id>   # hedges, the source's voice; --fix mends
```

Rerun step 0. Then read ten of the new memories, `summary`, `quote` and
`enrichment`, against the bars: *glad to know*, and *needs its spot*. Great
is one moment with a person in it (Andersen fed a sausage sandwich at the play,
9735's "So - you're still alive?"); dull is a record (owners and rebuilds,
sabotage damage, opening hours, what used to stand here, a narrator's errand).
More than one dull in ten means pause the source. If the
memories are weak, the fix goes into the pipeline (prompt, judge, source
choice), not into verdicts. Run the database writes yourself (`dedup --apply`,
`sources set`, `walk_score --all`); the founder doesn't want them handed over.

## 6. Log and report

- Append one line to `docs/04-extract.md` § *Road to coverage (Copenhagen)*:
  date, source, items, memories, good, mean `walk_score`, $ if known, and
  coverage after the pass (`toward_goal`, full and empty cells).
- Tell the user: coverage **X / 1530** (full and empty cells), good overall,
  what this pass added, and the next source step 2 would pick.
- Friction goes in `TODO.md` per AGENTS.md. Then commit and push.

## Don't

- Run `pipeline.extract`, `enqueue --all` or `pipeline.run_all`. Each one bills
  everything pending, across every source.
- Move the count by hand: no hiding, accepting, rescoring or bbox games.
- Kill a batch, or run two at once.
- Touch `loop/*`. That's the app build loop.
