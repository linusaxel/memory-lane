# Content Ingestion

## Purpose

Read content URLs from `config/content.yaml` and insert them into the `content` table.

## Behavior

- **Idempotent**: Running multiple times won't create duplicates
- Extracts platform-specific IDs (e.g., YouTube video ID from URL)
- Stores optional metadata (title, source name)

## Config Format

```yaml
sources:
  - name: "Channel Name"
    platform: youtube

    # Optional: auto-discover the channel's videos (via yt-dlp).
    # Title and publish date come back with each video.
    channel: "https://www.youtube.com/@handle"
    limit: 25                 # omit to ingest the entire channel

    # Optional: hand-listed videos. Can be combined with `channel:` -
    # both lists are merged and deduped on the normalized URL.
    videos:
      - url: "https://www.youtube.com/watch?v=VIDEO_ID"
        title: "Optional Title Override"
      - url: "https://www.youtube.com/watch?v=ANOTHER_ID"
```

A source needs `channel:`, `videos:`, or both. Re-running ingest is idempotent:
already-known URLs are skipped, so discovering a channel repeatedly only ever
inserts what is new.

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
