# Memory Lane: Project Specification

## Overview

Memory Lane extracts "memories" from video content—specific experiences that happened at identifiable physical locations—and makes them queryable by geographic proximity.

## What is a Memory?

A memory is something that **happened** at a **specific physical location**.

### Qualifies as a memory:
- Personal experiences: "I proposed to my wife on this bridge"
- Specific events: "We had dinner at a restaurant in the Latin Quarter"
- Vivid recollections: "I got lost in the medina and found this incredible spice market"

### Does NOT qualify:
- Hypotheticals: "I want to visit Paris someday"
- Vague references: "Somewhere in Europe"
- General facts: "Paris is the capital of France"
- Recommendations without personal experience: "You should check out the Eiffel Tower"

## Pipeline Stages

```
Content URLs → Transcripts → LLM Extraction (with coords) → Query API
```

1. **Ingest** - Load content URLs from configuration
2. **Transcripts** - Fetch video transcripts with timestamps
3. **Extract** - LLM identifies memories *and emits lat/lng directly*
4. **API** - Serve nearby memories by lat/lng query

There is no separate geocoding stage. Claude returns coordinates as part of
extraction; `pipeline/geocode.py` only reports on what it produced.

## Data Model

### Core Entities

- **Content** - Video/audio sources (YouTube videos, podcasts)
- **Transcript** - Timestamped text segments
- **Place** - Geographic locations with coordinates
- **Memory** - Extracted experiences linking content to places

### Relationships

```
Content (1) ──── (1) Transcript
    │
    └── (1) ──── (*) Memory ──── (*) ──── (1) Place
```

## Key Design Decisions

### Chunking Strategy
- Transcripts split into 4-minute chunks with 30-second overlap
- Prevents missing memories at chunk boundaries
- Timestamp markers preserved for accurate linking

### Location Precision Levels
| Level | Accuracy | Example |
|-------|----------|---------|
| exact | ~50m | Specific venue/address |
| street | ~200m | Street or intersection |
| neighborhood | ~1km | General area |
| city | ~10km | City-level only |

### Confidence Scoring
- **high** - Clear location, definite event
- **medium** - Location somewhat vague or event unclear
- **low** - Uncertain, might not geocode well (filtered out)

## Tech Stack

- **Database**: PostgreSQL + PostGIS
- **LLM**: Claude (Anthropic API) - handles both extraction and geocoding
- **API**: FastAPI
- **Transcripts**: youtube-transcript-api
