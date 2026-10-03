# Memory Lane: Project Specification

## In one paragraph

The product in plain words, for anything public-facing (store listing, a
landing page, a pitch). Keep it word for word.

> Memory Lane is a walk planner with memories along the way. Each day it plans
> a walk past real stories pinned to the places they happened, some from travel
> shows and podcasts and some left by people who were there, and a story only
> opens once you're standing on its spot. It's meant to make a familiar walk
> feel new, because the ordinary corner you pass every day turns out to have a
> story.

## Overview

Memory Lane pins "memories" (specific experiences that happened at
identifiable physical locations) to the places they happened. They come from
two sources: extracted by an LLM from travel-show and podcast transcripts, or
filed from the phone of somebody standing on the spot. Each day the app plans
a short walk past a few of them, and a memory can only be read from within
`UNLOCK_RADIUS_METERS` of its place.

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
extraction as a fallback; free geocoders (Photon, Wikidata) place the
venue or address it names first
(docs/10-decisions.md#the-llm-names-the-place-free-geocoders-place-it).

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
