---
name: make-memories
description: Resume making Memory Lane memories toward the goal of 1,000 good ones in Copenhagen. One pass per kick-off - progress, pick the best source, ask, batch-extract, check, log. Use when asked to make, resume or continue memory creation, or to say how far we are from 1k.
---

# Make memories

**Goal: 1,000 good memories in Copenhagen.** Good means visible, not a user's,
inside the launch bbox, and `walk_score >= 7`. The database is the state: every
pass starts by counting, so there is nothing to resume by hand.
Scores from 2026-10-05 on are stricter (docs/10, *The walk score asks one
question*), so a source's old good-per-item overstates its yield now.

One pass, one source. Every step is free except the one marked **bills**, and
that one waits for a yes.

All SQL runs as `docker exec memory-lane-db-1 psql -U memorylane -d memorylane -c "<sql>"`.

## 0. Where are we (free)

```sql
SELECT count(*) FILTER (WHERE NOT m.hidden) visible,
       count(*) FILTER (WHERE NOT m.hidden AND m.walk_score >= 7) good,
       count(*) FILTER (WHERE NOT m.hidden AND m.walk_score IS NULL) unscored,
       1000 - count(*) FILTER (WHERE NOT m.hidden AND m.walk_score >= 7) to_go
FROM memories m JOIN places p ON p.id = m.place_id
WHERE m.user_id IS NULL
  AND ST_Y(p.coordinates::geometry) BETWEEN 55.60 AND 55.74
  AND ST_X(p.coordinates::geometry) BETWEEN 12.45 AND 12.66;
```

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
         count(m.id) FILTER (WHERE NOT m.hidden AND m.walk_score >= 7) good
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
- **A source with fewer than 5 items done gets a trial first**: run
  `batch --content <5 ids>` with those five ids. Its `expected` is a guess
  until then.
- If a source's done items average under 7, suggest
  `! venv/bin/python -m pipeline.sources set <id> paused --note "<why>"` to the user and skip it.

## 3. Thin backlog: find new sources

If the best `expected` is under about 50, or nothing is pending, follow
`.claude/skills/find-sources/SKILL.md` steps 1-4 instead. Its step 5 trial
comes back through step 4 here: ask first, and batch rather than worker.

## 4. Ask, then batch (**bills**)

```bash
venv/bin/python -m pipeline.batch --source "<exact name>"   # dry: counts pending
```

Tell the user the items, the expected good memories, and the estimated cost.
Use the source's own $/memory from `docs/04-extract.md` § Road to 1,000 if a
run has been logged; otherwise use about $0.25 per memory extracted, which is
about 2× the expected good count. Ask with AskUserQuestion. On a yes, start it
with `run_in_background` and wait for the notification. Don't poll.

```bash
venv/bin/python -m pipeline.batch --source "<exact name>" --run
```

A batch takes minutes to hours, and each pass polls every 30 s. If it exits
with "stored nothing", stop and report. Don't retry.

## 5. Check what it made (free)

```bash
venv/bin/python -m pipeline.dedup --memories --source <id>   # dry run: retellings
```

Rerun step 0. Then read ten of the new memories, `summary`, `quote` and
`enrichment`, against the bars: *glad to know*, and *needs its spot*. If the
memories are weak, the fix goes into the pipeline (prompt, judge, source
choice), not into verdicts. Hand every database write (`dedup --apply`,
`review`, `sources set`) to the user as a `!` command.

## 6. Log and report

- Append one line to `docs/04-extract.md` § *Road to 1,000 (Copenhagen)*:
  date, source, items, memories, good, mean `walk_score`, $ if known.
- Tell the user: good **X / 1000**, what this pass added, and the next source
  step 2 would pick.
- Friction goes in `TODO.md` per AGENTS.md. Then commit and push.

## Don't

- Run `pipeline.extract`, `enqueue --all` or `pipeline.run_all`. Each one bills
  everything pending, across every source.
- Move the count by hand: no hiding, accepting, rescoring or bbox games.
- Kill a batch, or run two at once.
- Touch `loop/*`. That's the app build loop.
