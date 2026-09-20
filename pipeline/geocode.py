"""Geocode places using LLM-provided coordinates.

The extraction step now includes lat/lng estimates from Claude directly.
This module provides utilities for places that may need re-geocoding or
verification.
"""

import logging

from sqlalchemy import text

from pipeline.db import get_session

logger = logging.getLogger(__name__)


def get_places_stats():
    """Get statistics about geocoded places."""
    with get_session() as session:
        stats = session.execute(
            text("""
                SELECT
                    geocode_status,
                    COUNT(*) as count
                FROM places
                GROUP BY geocode_status
            """)
        ).fetchall()

        return {row[0]: row[1] for row in stats}


def list_places_without_coordinates():
    """List places that don't have coordinates."""
    with get_session() as session:
        places = session.execute(
            text("""
                SELECT id, name, place_query, geocode_status
                FROM places
                WHERE coordinates IS NULL
            """)
        ).fetchall()

        return [
            {"id": row[0], "name": row[1], "place_query": row[2], "status": row[3]}
            for row in places
        ]


def update_place_coordinates(place_id: int, lat: float, lng: float, status: str = "manual"):
    """Manually update coordinates for a place."""
    with get_session() as session:
        session.execute(
            text("""
                UPDATE places SET
                    coordinates = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                    geocode_status = :status,
                    geocoded_at = CURRENT_TIMESTAMP
                WHERE id = :id
            """),
            {"id": place_id, "lat": lat, "lng": lng, "status": status},
        )
        logger.info(f"Updated place {place_id} with coordinates ({lat}, {lng})")


def geocode_pending_places():
    """Report on places pending geocoding.

    Since LLM extraction now provides coordinates directly, this just
    reports status rather than calling an external API.
    """
    stats = get_places_stats()
    missing = list_places_without_coordinates()

    logger.info(f"Place geocoding stats: {stats}")

    if missing:
        logger.warning(f"Found {len(missing)} places without coordinates:")
        for place in missing:
            logger.warning(f"  - {place['name']} (query: {place['place_query']})")
    else:
        logger.info("All places have coordinates")

    return {
        "stats": stats,
        "missing": len(missing),
        "missing_places": missing,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    geocode_pending_places()
