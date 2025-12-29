"""FastAPI application for Memory Lane API."""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy import text

from pipeline.db import get_session

app = FastAPI(
    title="Memory Lane API",
    description="Query location-based memories from video content",
    version="1.0.0"
)

# CORS for web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# MODELS
# ============================================================================

class Coordinates(BaseModel):
    lat: float
    lng: float


class Place(BaseModel):
    id: int
    name: str
    coordinates: Optional[Coordinates] = None
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
    distance_meters: Optional[float] = None
    content: ContentRef
    tags: list[str]
    confidence: str


class NearbyMeta(BaseModel):
    total: int
    limit: int
    offset: int
    center: Coordinates
    radius_km: float


class NearbyResponse(BaseModel):
    memories: list[Memory]
    meta: NearbyMeta


class PlaceWithCount(BaseModel):
    id: int
    name: str
    coordinates: Optional[Coordinates] = None
    distance_meters: Optional[float] = None
    memory_count: int
    tags: list[str]
    sample_memory: Optional[str] = None


class PlacesResponse(BaseModel):
    places: list[PlaceWithCount]
    meta: NearbyMeta


class PlaceDetail(BaseModel):
    id: int
    name: str
    place_query: str
    coordinates: Optional[Coordinates] = None
    precision_meters: int
    geocode_status: str
    memory_count: int
    tags: list[str]


class ContentSummary(BaseModel):
    id: int
    title: Optional[str]
    url: str
    memory_count: int


# ============================================================================
# QUERIES
# ============================================================================

NEARBY_MEMORIES_QUERY = """
SELECT
    m.id,
    m.summary,
    m.timestamp_start,
    m.timestamp_end,
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
    AND (:min_confidence = 'low' OR m.extraction_confidence IN ('medium', 'high'))
    AND (:min_confidence != 'high' OR m.extraction_confidence = 'high')
ORDER BY distance_meters ASC
LIMIT :limit OFFSET :offset
"""

NEARBY_MEMORIES_WITH_TAGS_QUERY = """
SELECT
    m.id,
    m.summary,
    m.timestamp_start,
    m.timestamp_end,
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
    AND m.tags && CAST(:tags AS varchar[])
    AND (:min_confidence = 'low' OR m.extraction_confidence IN ('medium', 'high'))
    AND (:min_confidence != 'high' OR m.extraction_confidence = 'high')
ORDER BY distance_meters ASC
LIMIT :limit OFFSET :offset
"""

COUNT_QUERY = """
SELECT COUNT(*)
FROM memories m
JOIN places p ON m.place_id = p.id
WHERE
    p.coordinates IS NOT NULL
    AND ST_DWithin(
        p.coordinates,
        ST_MakePoint(:lng, :lat)::geography,
        :radius_meters
    )
"""

NEARBY_PLACES_QUERY = """
SELECT
    p.id,
    p.name,
    p.precision_meters,
    ST_Y(p.coordinates::geometry) as lat,
    ST_X(p.coordinates::geometry) as lng,
    ST_Distance(p.coordinates, ST_MakePoint(:lng, :lat)::geography) as distance_meters,
    COUNT(m.id) as memory_count,
    COALESCE(
        (SELECT array_agg(DISTINCT t) FROM memories m2, unnest(m2.tags) t WHERE m2.place_id = p.id),
        ARRAY[]::varchar[]
    ) as tags,
    (SELECT summary FROM memories WHERE place_id = p.id ORDER BY id LIMIT 1) as sample_memory
FROM places p
JOIN memories m ON m.place_id = p.id
WHERE
    p.coordinates IS NOT NULL
    AND ST_DWithin(
        p.coordinates,
        ST_MakePoint(:lng, :lat)::geography,
        :radius_meters
    )
GROUP BY p.id, p.name, p.precision_meters, p.coordinates
ORDER BY distance_meters ASC
LIMIT :limit OFFSET :offset
"""

SINGLE_MEMORY_QUERY = """
SELECT
    m.id,
    m.summary,
    m.timestamp_start,
    m.timestamp_end,
    m.tags,
    m.extraction_confidence,
    m.created_at,
    p.id as place_id,
    p.name as place_name,
    p.precision_meters,
    ST_Y(p.coordinates::geometry) as lat,
    ST_X(p.coordinates::geometry) as lng,
    c.id as content_id,
    c.title as content_title,
    c.url as content_url
FROM memories m
JOIN places p ON m.place_id = p.id
JOIN content c ON m.content_id = c.id
WHERE m.id = :memory_id
"""

PLACE_MEMORIES_QUERY = """
SELECT
    m.id,
    m.summary,
    m.timestamp_start,
    m.timestamp_end,
    m.tags,
    m.extraction_confidence,
    p.id as place_id,
    p.name as place_name,
    p.precision_meters,
    ST_Y(p.coordinates::geometry) as lat,
    ST_X(p.coordinates::geometry) as lng,
    c.id as content_id,
    c.title as content_title,
    c.url as content_url
FROM memories m
JOIN places p ON m.place_id = p.id
JOIN content c ON m.content_id = c.id
WHERE p.id = :place_id
ORDER BY m.created_at DESC
LIMIT :limit OFFSET :offset
"""

SINGLE_PLACE_QUERY = """
SELECT
    p.id,
    p.name,
    p.place_query,
    p.precision_meters,
    p.geocode_status,
    ST_Y(p.coordinates::geometry) as lat,
    ST_X(p.coordinates::geometry) as lng,
    p.created_at,
    COUNT(m.id) as memory_count,
    COALESCE(
        (SELECT array_agg(DISTINCT t) FROM memories m2, unnest(m2.tags) t WHERE m2.place_id = p.id),
        ARRAY[]::varchar[]
    ) as tags
FROM places p
LEFT JOIN memories m ON m.place_id = p.id
WHERE p.id = :place_id
GROUP BY p.id, p.name, p.place_query, p.precision_meters, p.geocode_status, p.coordinates, p.created_at
"""

CONTENT_MEMORIES_QUERY = """
SELECT
    m.id,
    m.summary,
    m.timestamp_start,
    m.timestamp_end,
    m.tags,
    m.extraction_confidence,
    p.id as place_id,
    p.name as place_name,
    p.precision_meters,
    ST_Y(p.coordinates::geometry) as lat,
    ST_X(p.coordinates::geometry) as lng,
    c.id as content_id,
    c.title as content_title,
    c.url as content_url
FROM memories m
JOIN places p ON m.place_id = p.id
JOIN content c ON m.content_id = c.id
WHERE c.id = :content_id
ORDER BY m.timestamp_start ASC
LIMIT :limit OFFSET :offset
"""


# ============================================================================
# HELPERS
# ============================================================================

def row_to_memory(row, include_distance: bool = True) -> Memory:
    """Convert database row to Memory model."""
    coords = None
    if row.lat is not None and row.lng is not None:
        coords = Coordinates(lat=row.lat, lng=row.lng)

    timestamp_url = row.content_url
    if "youtube.com" in row.content_url or "youtu.be" in row.content_url:
        separator = "&" if "?" in row.content_url else "?"
        timestamp_url = f"{row.content_url}{separator}t={int(row.timestamp_start)}"

    return Memory(
        id=row.id,
        summary=row.summary,
        place=Place(
            id=row.place_id,
            name=row.place_name,
            coordinates=coords,
            precision_meters=row.precision_meters
        ),
        distance_meters=row.distance_meters if include_distance and hasattr(row, 'distance_meters') else None,
        content=ContentRef(
            id=row.content_id,
            title=row.content_title,
            url=row.content_url,
            timestamp_start=row.timestamp_start,
            timestamp_url=timestamp_url
        ),
        tags=row.tags or [],
        confidence=row.extraction_confidence or "medium"
    )


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """API root - health check."""
    return {"status": "ok", "service": "memory-lane"}


@app.get("/v1/memories/nearby", response_model=NearbyResponse)
async def get_nearby_memories(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude"),
    radius_km: float = Query(10, ge=0.1, le=100, description="Search radius in km"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    tags: Optional[str] = Query(None, description="Comma-separated tags to filter"),
    min_confidence: str = Query("medium", pattern="^(low|medium|high)$", description="Minimum confidence")
):
    """Find memories near a location."""
    radius_meters = radius_km * 1000

    with get_session() as session:
        params = {
            "lat": lat,
            "lng": lng,
            "radius_meters": radius_meters,
            "limit": limit,
            "offset": offset,
            "min_confidence": min_confidence
        }

        if tags:
            tag_list = [t.strip() for t in tags.split(",")]
            params["tags"] = tag_list
            result = session.execute(text(NEARBY_MEMORIES_WITH_TAGS_QUERY), params)
        else:
            result = session.execute(text(NEARBY_MEMORIES_QUERY), params)

        rows = result.fetchall()

        # Get total count
        count_result = session.execute(
            text(COUNT_QUERY),
            {"lat": lat, "lng": lng, "radius_meters": radius_meters}
        )
        total = count_result.scalar() or 0

    memories = [row_to_memory(row) for row in rows]

    return NearbyResponse(
        memories=memories,
        meta=NearbyMeta(
            total=total,
            limit=limit,
            offset=offset,
            center=Coordinates(lat=lat, lng=lng),
            radius_km=radius_km
        )
    )


@app.get("/v1/memories/{memory_id}", response_model=Memory)
async def get_memory(memory_id: int):
    """Get a single memory by ID."""
    with get_session() as session:
        result = session.execute(
            text(SINGLE_MEMORY_QUERY),
            {"memory_id": memory_id}
        )
        row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Memory not found")

    return row_to_memory(row, include_distance=False)


@app.get("/v1/places/nearby", response_model=PlacesResponse)
async def get_nearby_places(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude"),
    radius_km: float = Query(10, ge=0.1, le=100, description="Search radius in km"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """Get places with memory counts near a location."""
    radius_meters = radius_km * 1000

    with get_session() as session:
        result = session.execute(
            text(NEARBY_PLACES_QUERY),
            {
                "lat": lat,
                "lng": lng,
                "radius_meters": radius_meters,
                "limit": limit,
                "offset": offset
            }
        )
        rows = result.fetchall()

    places = []
    for row in rows:
        coords = None
        if row.lat is not None and row.lng is not None:
            coords = Coordinates(lat=row.lat, lng=row.lng)

        places.append(PlaceWithCount(
            id=row.id,
            name=row.name,
            coordinates=coords,
            distance_meters=row.distance_meters,
            memory_count=row.memory_count,
            tags=row.tags or [],
            sample_memory=row.sample_memory
        ))

    return PlacesResponse(
        places=places,
        meta=NearbyMeta(
            total=len(places),
            limit=limit,
            offset=offset,
            center=Coordinates(lat=lat, lng=lng),
            radius_km=radius_km
        )
    )


@app.get("/v1/places/{place_id}", response_model=PlaceDetail)
async def get_place(place_id: int):
    """Get details for a specific place."""
    with get_session() as session:
        result = session.execute(
            text(SINGLE_PLACE_QUERY),
            {"place_id": place_id}
        )
        row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Place not found")

    coords = None
    if row.lat is not None and row.lng is not None:
        coords = Coordinates(lat=row.lat, lng=row.lng)

    return PlaceDetail(
        id=row.id,
        name=row.name,
        place_query=row.place_query,
        coordinates=coords,
        precision_meters=row.precision_meters,
        geocode_status=row.geocode_status,
        memory_count=row.memory_count,
        tags=row.tags or []
    )


@app.get("/v1/places/{place_id}/memories", response_model=list[Memory])
async def get_place_memories(
    place_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get all memories for a specific place."""
    with get_session() as session:
        result = session.execute(
            text(PLACE_MEMORIES_QUERY),
            {"place_id": place_id, "limit": limit, "offset": offset}
        )
        rows = result.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="Place not found or has no memories")

    return [row_to_memory(row, include_distance=False) for row in rows]


@app.get("/v1/content/{content_id}/memories", response_model=list[Memory])
async def get_content_memories(
    content_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get all memories extracted from a specific video/content."""
    with get_session() as session:
        result = session.execute(
            text(CONTENT_MEMORIES_QUERY),
            {"content_id": content_id, "limit": limit, "offset": offset}
        )
        rows = result.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="Content not found or has no memories")

    return [row_to_memory(row, include_distance=False) for row in rows]


@app.get("/v1/stats")
async def get_stats():
    """Get database statistics."""
    with get_session() as session:
        memories_count = session.execute(text("SELECT COUNT(*) FROM memories")).scalar()
        places_count = session.execute(text("SELECT COUNT(*) FROM places WHERE coordinates IS NOT NULL")).scalar()
        content_count = session.execute(text("SELECT COUNT(*) FROM content WHERE memories_extracted = TRUE")).scalar()

    return {
        "memories": memories_count,
        "places_with_coordinates": places_count,
        "processed_videos": content_count
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
