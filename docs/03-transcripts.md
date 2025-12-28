# Transcript Fetching

## Purpose

Fetch transcripts for all content where `transcript_fetched = FALSE`. Store as JSONB with timestamps preserved.

## Transcript Format

```json
{
  "segments": [
    {"text": "Welcome to the show.", "start": 0.0, "duration": 2.5},
    {"text": "Today we're talking about...", "start": 2.5, "duration": 3.1}
  ]
}
```

## Language Priority

For YouTube videos, transcripts are fetched in order of preference:
1. Manually created English transcript
2. Auto-generated English transcript
3. Any English variant (en-US, en-GB, etc.)

## Error Handling

| Condition | Action |
|-----------|--------|
| Transcripts disabled | Mark `transcript_failed = TRUE` |
| Video unavailable | Mark `transcript_failed = TRUE` |
| No English transcript | Mark `transcript_failed = TRUE` |
| Network error | Leave as pending for retry |

## Processing Notes

- Failed content is excluded from the extraction stage
- `full_text` column stores concatenated segments for quick access
- Language code is preserved for reference
