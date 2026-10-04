# Content Ingestion

## Purpose

Poll the `active` YouTube channels in the `sources` table and insert their videos into
the `content` table. Finding and judging sources is `pipeline/sources.py`; see
[Sources are rows with a status](10-decisions.md#sources-are-rows-with-a-status).

## Behavior

- **Idempotent**: Running multiple times won't create duplicates
- Extracts platform-specific IDs (e.g., YouTube video ID from URL)
- Stores optional metadata (title, source name)

## Sources

```bash
python -m pipeline.sources list                       # every source, best yield first
python -m pipeline.sources add youtube_channel https://www.youtube.com/@handle "Name"
python -m pipeline.sources screen <id>                # Haiku on 3 items, no Sonnet
python -m pipeline.ingest --video <url> --to <id>     # one trial episode
python -m pipeline.sources set <id> active            # ingest now polls it
```

Text sources (`crawler/sources.py`) take `--source <key> --query <q>`: books,
old newspapers, Historisk Atlas, OSM plaques (`plaques`, a box), Wikipedia
near a point (`wikipedia`), film locations (`filming`, a box), a press feed
(`press`) and a podcast feed with transcripts (`podcast`). How to find and
trial a new one is the `find-sources` skill (`.claude/skills/find-sources/`).

Only `active` channels are polled, `poll_limit` newest videos each (NULL is the
whole channel). A `candidate`'s or `rejected` source's items are ingested only
to be screened, and bulk extraction (`enqueue --all`) skips them. Re-running
ingest is idempotent: already-known URLs are skipped.

## Supported Platforms

| Platform | URL Patterns |
|----------|--------------|
| youtube | youtube.com/watch?v=, youtu.be/, youtube.com/embed/ |

## URL Parsing

YouTube video IDs are 11 characters and extracted from various URL formats:
- `https://www.youtube.com/watch?v=CDWPxEmBWCQ`
- `https://youtu.be/CDWPxEmBWCQ`
- `https://www.youtube.com/embed/CDWPxEmBWCQ`

## Output

After ingestion, the `content` table contains:
- Normalized URL
- Platform identifier
- Platform-specific ID
- Source/channel name
- Optional title

## Validation

```sql
SELECT platform, source_name, COUNT(*)
FROM content
GROUP BY platform, source_name;
```
