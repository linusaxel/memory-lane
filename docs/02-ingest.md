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
    videos:
      - url: "https://www.youtube.com/watch?v=VIDEO_ID"
        title: "Optional Title Override"
      - url: "https://www.youtube.com/watch?v=ANOTHER_ID"
```

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
