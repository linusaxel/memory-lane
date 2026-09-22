# Scaling Architecture & API Design

> **Status: design notes, not a description of the code.** Written before the
> API existed. Parts of it shipped — the two-stage Haiku/Sonnet queue in
> `pipeline/tasks.py` and the `/v1/memories/*` endpoints. Parts never did: the
> transcript-layer queue, the distributed rate limiter, the retry decorator and
> the dead-letter queue. The inline code samples are sketches and have drifted
> from the real files; treat `api/main.py`, `pipeline/tasks.py` and CLAUDE.md as
> the source of truth, and this file as the reasoning behind them.

## Target Scale

**Reasonable scale definition:**
- 500-1,000 videos/day ingested
- ~10,000-50,000 memories extracted/day
- API: 100-1,000 req/min for location queries
- Latency: Extraction within 5-10 min of ingest, API p95 < 200ms

---

## Part 1: Scalable Extraction Pipeline

### Current Bottlenecks

1. **Sequential chunk processing** - One API call at a time
2. **Single-process execution** - No horizontal scaling
3. **No retry/queue mechanism** - Failures require manual rerun
4. **No cost controls** - All chunks hit Claude equally

### Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           INGESTION LAYER                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   Content Sources ──► Ingest Worker ──► PostgreSQL (content table)      │
│   (YouTube, etc.)         │                                              │
│                           ▼                                              │
│                    Redis Queue: "pending_transcripts"                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         TRANSCRIPT LAYER                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│   │ Transcript   │  │ Transcript   │  │ Transcript   │   (N workers)    │
│   │ Worker 1     │  │ Worker 2     │  │ Worker 3     │                  │
│   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                  │
│          │                 │                 │                           │
│          └────────────────┬┴─────────────────┘                          │
│                           ▼                                              │
│                    Redis Queue: "pending_extraction"                     │
│                    (one message per CHUNK, not per video)                │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         EXTRACTION LAYER                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│   │ Extract      │  │ Extract      │  │ Extract      │   (N workers)    │
│   │ Worker 1     │  │ Worker 2     │  │ Worker N     │                  │
│   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                  │
│          │                 │                 │                           │
│          │    Anthropic API (rate-limited, shared semaphore)            │
│          │                 │                 │                           │
│          └────────────────┬┴─────────────────┘                          │
│                           ▼                                              │
│                    Redis Queue: "extracted_memories"                     │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          AGGREGATION LAYER                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   Aggregator Worker:                                                     │
│   - Collects all chunks for a content_id                                │
│   - Runs merge_nearby_memories()                                        │
│   - Runs filter_low_confidence()                                        │
│   - Writes to PostgreSQL                                                │
│   - Marks content as extracted                                          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

#### 1. Queue per Chunk (not per Video)

```python
# After transcript fetch, enqueue each chunk separately
chunks = chunk_transcript(segments)
for i, chunk in enumerate(chunks):
    queue.enqueue("pending_extraction", {
        "content_id": content_id,
        "chunk_index": i,
        "total_chunks": len(chunks),
        "chunk_text": chunk
    })
```

**Why:** Enables parallel extraction across workers. A 60-min video (15 chunks) can be processed by 15 workers simultaneously.

#### 2. Rate Limiting with Distributed Semaphore

```python
# Redis-based rate limiter (e.g., 50 concurrent API calls)
async with rate_limiter.acquire(max_concurrent=50, timeout=30):
    memories = await extract_memories_from_chunk(client, chunk)
```

**Why:** Anthropic API has rate limits. Shared semaphore prevents 429s across all workers.

#### 3. Two-Stage Cost Optimization

```python
# Stage 1: Fast classifier (Haiku) - "Does this chunk contain location memories?"
has_locations = await classify_chunk(haiku_client, chunk)  # ~$0.0001/chunk

# Stage 2: Full extraction (Sonnet) - only if Stage 1 says yes
if has_locations:
    memories = await extract_memories(sonnet_client, chunk)  # ~$0.003/chunk
```

**Savings:** If 40% of chunks have no memories, saves ~40% on extraction costs.

#### 4. Chunk Result Aggregation

```python
# Redis hash to track chunk completion
redis.hset(f"extraction:{content_id}", chunk_index, json.dumps(memories))
redis.hincrby(f"extraction:{content_id}:progress", "completed", 1)

# When all chunks done, trigger aggregation
if completed == total_chunks:
    queue.enqueue("aggregate", {"content_id": content_id})
```

### Tech Stack Recommendations

| Component | Recommendation | Why |
|-----------|---------------|-----|
| Queue | **Redis + RQ** or **Celery** | Simple, Python-native, good for this scale |
| Workers | **Python + asyncio** | Anthropic SDK supports async |
| Rate Limiting | **redis-semaphore** | Distributed, battle-tested |
| Monitoring | **Prometheus + Grafana** | Track queue depth, latency, costs |
| Deployment | **Fly.io** or **Railway** | Simple scaling, no k8s overhead |

### Failure Handling

```python
# Retry with exponential backoff
@retry(max_attempts=3, backoff=[5, 30, 120])
async def extract_chunk(chunk_data):
    try:
        return await extract_memories_from_chunk(client, chunk_data["chunk_text"])
    except RateLimitError:
        raise RetryableError()
    except BillingError:
        raise FatalError()  # Don't retry, alert ops

# Dead letter queue for manual inspection
if attempts_exhausted:
    queue.enqueue("extraction_dlq", chunk_data)
```

### Estimated Throughput

| Workers | Chunks/min | Videos/hour (avg 10 chunks) | API Cost/hour |
|---------|------------|----------------------------|---------------|
| 5 | 60 | 360 | ~$6.50 |
| 10 | 120 | 720 | ~$13.00 |
| 20 | 240 | 1,440 | ~$26.00 |

*Assuming 3s avg per Claude Sonnet call, ~$0.003/chunk*

---

## Part 2: Location-Based Memories API

### API Overview

RESTful API for querying memories by geographic proximity.

**Base URL:** `http://localhost:8080/v1` locally. Nothing is deployed yet;
the hostname below is illustrative.

### Endpoints

#### `GET /memories/nearby`

Find memories near a location.

**Query Parameters:**

| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `lat` | float | Yes | - | Latitude (-90 to 90) |
| `lng` | float | Yes | - | Longitude (-180 to 180) |
| `radius_km` | float | No | 10 | Search radius in kilometers (max 100) |
| `limit` | int | No | 20 | Max results (max 100) |
| `offset` | int | No | 0 | Pagination offset |
| `tags` | string | No | - | Comma-separated tags to filter |
| `min_confidence` | string | No | medium | Minimum confidence: low, medium, high |

**Example Request:**
```bash
curl "https://api.memorylane.dev/v1/memories/nearby?lat=40.7484&lng=-73.9857&radius_km=5&tags=food,culture"
```

**Example Response:**
```json
{
  "memories": [
    {
      "id": 42,
      "summary": "Mark tried the pastrami sandwich at Katz's Deli and couldn't stop talking about how the meat was sliced by hand, piled impossibly high. He made Joe wait 45 minutes in line and declared it 'worth every second.'",
      "place": {
        "id": 15,
        "name": "Katz's Delicatessen",
        "coordinates": {
          "lat": 40.7223,
          "lng": -73.9874
        },
        "precision_meters": 50
      },
      "distance_meters": 2847,
      "content": {
        "id": 7,
        "title": "NYC Food Tour - Best Delis",
        "url": "https://youtube.com/watch?v=abc123&t=847",
        "timestamp_start": 847.5
      },
      "tags": ["food", "culture"],
      "confidence": "high"
    }
  ],
  "meta": {
    "total": 156,
    "limit": 20,
    "offset": 0,
    "center": {"lat": 40.7484, "lng": -73.9857},
    "radius_km": 5
  }
}
```

#### `GET /memories/:id`

Get a single memory by ID.

**Example Response:**
```json
{
  "id": 42,
  "summary": "...",
  "place": { ... },
  "content": { ... },
  "tags": ["food", "culture"],
  "confidence": "high",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### `GET /places/nearby`

Get places (with memory counts) near a location.

**Query Parameters:** Same as `/memories/nearby`

**Example Response:**
```json
{
  "places": [
    {
      "id": 15,
      "name": "Katz's Delicatessen",
      "coordinates": {"lat": 40.7223, "lng": -73.9874},
      "distance_meters": 2847,
      "memory_count": 3,
      "tags": ["food", "culture"],
      "sample_memory": "Mark tried the pastrami sandwich..."
    }
  ]
}
```

#### `GET /places/:id/memories`

Get all memories for a specific place.

### SQL Query (Core Logic)

```sql
-- /memories/nearby implementation
SELECT
    m.id,
    m.summary,
    m.timestamp_start,
    m.tags,
    m.extraction_confidence,
    p.id as place_id,
    p.name as place_name,
    p.precision_meters,
    ST_Y(p.coordinates::geometry) as lat,
    ST_X(p.coordinates::geometry) as lng,
    ST_Distance(p.coordinates, ST_MakePoint(:lng, :lat)::geography) as distance_meters,
    c.id as content_id,
    c.title as content_title,
    c.url as content_url
FROM memories m
JOIN places p ON m.place_id = p.id
JOIN content c ON m.content_id = c.id
WHERE
    p.coordinates IS NOT NULL
    AND ST_DWithin(
        p.coordinates,
        ST_MakePoint(:lng, :lat)::geography,
        :radius_meters
    )
    AND (:tags IS NULL OR m.tags && :tags::varchar[])
    AND m.extraction_confidence >= :min_confidence
ORDER BY distance_meters ASC
LIMIT :limit OFFSET :offset;
```

### Implementation Skeleton

```python
# api/main.py
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from pipeline.db import get_session
from sqlalchemy import text

app = FastAPI(title="Memory Lane API", version="1.0.0")

class Coordinates(BaseModel):
    lat: float
    lng: float

class Place(BaseModel):
    id: int
    name: str
    coordinates: Coordinates
    precision_meters: int

class ContentRef(BaseModel):
    id: int
    title: Optional[str]
    url: str
    timestamp_start: float
    timestamp_url: str

class Memory(BaseModel):
    id: int
    summary: str
    place: Place
    distance_meters: float
    content: ContentRef
    tags: list[str]
    confidence: str

class NearbyResponse(BaseModel):
    memories: list[Memory]
    meta: dict

@app.get("/v1/memories/nearby", response_model=NearbyResponse)
async def get_nearby_memories(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(10, ge=0.1, le=100),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tags: Optional[str] = Query(None),
    min_confidence: str = Query("medium", regex="^(low|medium|high)$")
):
    radius_meters = radius_km * 1000
    tag_list = tags.split(",") if tags else None

    with get_session() as session:
        result = session.execute(
            text(NEARBY_QUERY),
            {
                "lat": lat,
                "lng": lng,
                "radius_meters": radius_meters,
                "limit": limit,
                "offset": offset,
                "tags": tag_list,
                "min_confidence": min_confidence
            }
        )
        rows = result.fetchall()

    memories = [row_to_memory(row) for row in rows]

    return {
        "memories": memories,
        "meta": {
            "total": len(memories),  # TODO: separate count query
            "limit": limit,
            "offset": offset,
            "center": {"lat": lat, "lng": lng},
            "radius_km": radius_km
        }
    }

def row_to_memory(row) -> Memory:
    return Memory(
        id=row.id,
        summary=row.summary,
        place=Place(
            id=row.place_id,
            name=row.place_name,
            coordinates=Coordinates(lat=row.lat, lng=row.lng),
            precision_meters=row.precision_meters
        ),
        distance_meters=row.distance_meters,
        content=ContentRef(
            id=row.content_id,
            title=row.content_title,
            # api.gate.source_link resolves both, and returns no offset when
            # the source is not a recording.
            url=href,
            timestamp_start=offset,
        ),
        tags=row.tags or [],
        confidence=row.extraction_confidence
    )
```

### Performance Considerations

1. **PostGIS GIST Index** - Already exists (`idx_places_coordinates`)
2. **Connection Pooling** - Use pgbouncer or SQLAlchemy pool
3. **Caching** - Redis cache for popular locations (TTL 5-10 min)
4. **Pagination** - Cursor-based for large result sets

### Future Enhancements

- [ ] Clustering: Group nearby memories on map view
- [ ] Bounding box queries: `GET /memories/bbox?sw_lat=...&ne_lng=...`
- [x] Full-text search: `GET /v1/memories/search?q=pastrami` (shipped)
- [ ] User favorites/collections
- [ ] WebSocket for real-time updates when near a memory

---

## Summary

| Component | Current | Scaled |
|-----------|---------|--------|
| Extraction throughput | ~20 memories/min | ~500+ memories/min |
| Processing model | Both available: sequential and RQ workers | Parallel workers + queues |
| Failure handling | Manual rerun (no DLQ; not built) | Auto-retry + DLQ |
| API | FastAPI + PostGIS, containerized | same, horizontally scaled |
| Latency (API) | N/A | p95 < 200ms |