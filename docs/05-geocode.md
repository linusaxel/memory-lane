# Geocoding

## Purpose

Resolve `place_query` strings to geographic coordinates using Google Places API.

## API Choice

Google Places API (New) - Text Search endpoint. Provides best venue-level coverage globally.

## Request Fields

| Field | Value |
|-------|-------|
| Endpoint | `https://places.googleapis.com/v1/places:searchText` |
| Max results | 1 |
| Response fields | location, formattedAddress, id, displayName |

## Response Handling

Successful geocode returns:
- `lat` / `lng` coordinates
- `formatted_address` for verification
- `place_id` for reference
- `display_name` from Google

## Status Values

| Status | Meaning |
|--------|---------|
| pending | Not yet attempted |
| success | Coordinates found |
| failed | No results or error |

## Cost Estimation

Google Places Text Search: ~$32 per 1,000 requests

| Content items | Est. memories | Est. unique places | Cost |
|---------------|---------------|-------------------|------|
| 10 | 50 | 40 | ~$1.30 |
| 100 | 500 | 350 | ~$11 |
| 1,000 | 5,000 | 3,000 | ~$96 |

## Common Failure Reasons

- Too vague ("a cafe in Paris")
- Misspelled or garbled names
- Closed/demolished venues
- Non-existent places (LLM hallucination)

Failed places are marked `geocode_status = 'failed'` and excluded from API results.
