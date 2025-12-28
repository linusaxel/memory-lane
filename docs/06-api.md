# Query API

## Purpose

Serve nearby memories via HTTP. Read-only access to the database.

## Endpoint

```
GET /api/memories?lat={lat}&lng={lng}&radius_km={radius}
```

## Parameters

| Param | Type | Required | Default | Range |
|-------|------|----------|---------|-------|
| lat | float | yes | - | -90 to 90 |
| lng | float | yes | - | -180 to 180 |
| radius_km | float | no | 1.0 | 0.1 to 50 |
| limit | int | no | 50 | 1 to 100 |

## Response Format

```json
{
  "query": {
    "lat": 35.6762,
    "lng": 139.6503,
    "radius_km": 1.0
  },
  "count": 2,
  "memories": [
    {
      "id": 42,
      "summary": "The host describes finding a tiny ramen shop...",
      "tags": ["food", "travel"],
      "place": {
        "name": "Fuunji Ramen, Shibuya",
        "distance_meters": 127,
        "precision_meters": 50
      },
      "content": {
        "title": "My Japan Trip",
        "source_name": "The Tim Ferriss Show",
        "platform": "youtube",
        "deep_link": "https://youtube.com/watch?v=abc123&t=248",
        "timestamp_start": 248.2,
        "timestamp_end": 275.0
      }
    }
  ]
}
```

## Search Behavior

The search radius is adjusted by each place's `precision_meters`. A city-level memory (10km precision) will match from further away than an exact venue (50m precision).

## Deep Links

Platform-specific deep links jump directly to the timestamp:
- YouTube: `https://youtube.com/watch?v={id}&t={seconds}`

## Example Requests

```bash
# Find memories near Shibuya Station
curl "http://localhost:8000/api/memories?lat=35.6580&lng=139.7016&radius_km=0.5"

# Find memories in central Paris (larger radius)
curl "http://localhost:8000/api/memories?lat=48.8566&lng=2.3522&radius_km=2"
```

## Health Check

```
GET /health
```

Returns `{"status": "ok"}` when the service is running.
