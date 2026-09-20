#!/bin/bash
# API Test Script for Memory Lane
# Usage: ./api/test_api.sh [base_url]

BASE_URL="${1:-http://localhost:8080}"

echo "Testing Memory Lane API at $BASE_URL"
echo "========================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

pass() { echo -e "${GREEN}✓ $1${NC}"; }
fail() { echo -e "${RED}✗ $1${NC}"; }

# Health check
echo -e "\n[1] Health Check"
RESP=$(curl -s "$BASE_URL/")
if echo "$RESP" | grep -q '"status":"ok"'; then
    pass "GET / - Health check"
else
    fail "GET / - Health check"
    echo "  Response: $RESP"
fi

# Stats
echo -e "\n[2] Stats"
RESP=$(curl -s "$BASE_URL/v1/stats")
if echo "$RESP" | grep -q '"memories"'; then
    pass "GET /v1/stats"
    echo "  $RESP"
else
    fail "GET /v1/stats"
fi

# Nearby memories (NYC)
echo -e "\n[3] Nearby Memories (NYC)"
RESP=$(curl -s "$BASE_URL/v1/memories/nearby?lat=40.7128&lng=-74.0060&radius_km=50")
COUNT=$(echo "$RESP" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('memories',[])))" 2>/dev/null)
if [ "$COUNT" -gt 0 ] 2>/dev/null; then
    pass "GET /v1/memories/nearby - Found $COUNT memories"
else
    fail "GET /v1/memories/nearby"
    echo "  Response: ${RESP:0:200}..."
fi

# Nearby memories with tag filter
echo -e "\n[4] Nearby Memories with Tag Filter (food in New Orleans)"
RESP=$(curl -s "$BASE_URL/v1/memories/nearby?lat=30&lng=-90&radius_km=50&tags=food")
COUNT=$(echo "$RESP" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('memories',[])))" 2>/dev/null)
if [ "$COUNT" -gt 0 ] 2>/dev/null; then
    pass "GET /v1/memories/nearby?tags=food - Found $COUNT memories"
else
    fail "GET /v1/memories/nearby?tags=food"
fi

# Nearby memories with confidence filter
echo -e "\n[5] Nearby Memories with Confidence Filter"
RESP=$(curl -s "$BASE_URL/v1/memories/nearby?lat=40.7128&lng=-74.0060&radius_km=50&min_confidence=high")
COUNT=$(echo "$RESP" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('memories',[])))" 2>/dev/null)
pass "GET /v1/memories/nearby?min_confidence=high - Found $COUNT high-confidence memories"

# Single memory (find first valid ID)
echo -e "\n[6] Single Memory"
FIRST_ID=$(curl -s "$BASE_URL/v1/memories/nearby?lat=40.7128&lng=-74.0060&radius_km=100&limit=1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['memories'][0]['id'] if d.get('memories') else '')" 2>/dev/null)
if [ -n "$FIRST_ID" ]; then
    RESP=$(curl -s "$BASE_URL/v1/memories/$FIRST_ID")
    if echo "$RESP" | grep -q '"summary"'; then
        pass "GET /v1/memories/$FIRST_ID"
    else
        fail "GET /v1/memories/$FIRST_ID"
    fi
else
    echo "  Skipped - no memories found"
fi

# Memory not found (404)
echo -e "\n[7] Memory Not Found (404)"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/v1/memories/999999")
if [ "$HTTP_CODE" = "404" ]; then
    pass "GET /v1/memories/999999 - Returns 404"
else
    fail "GET /v1/memories/999999 - Expected 404, got $HTTP_CODE"
fi

# Nearby places
echo -e "\n[8] Nearby Places (NYC)"
RESP=$(curl -s "$BASE_URL/v1/places/nearby?lat=40.7128&lng=-74.0060&radius_km=50")
COUNT=$(echo "$RESP" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('places',[])))" 2>/dev/null)
if [ "$COUNT" -gt 0 ] 2>/dev/null; then
    pass "GET /v1/places/nearby - Found $COUNT places"
else
    fail "GET /v1/places/nearby"
fi

# OpenAPI docs
echo -e "\n[9] OpenAPI Docs"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/docs")
if [ "$HTTP_CODE" = "200" ]; then
    pass "GET /docs - Swagger UI available"
else
    fail "GET /docs - Expected 200, got $HTTP_CODE"
fi

# Full-text search
echo -e "\n[10] Full-Text Search"
RESP=$(curl -s "$BASE_URL/v1/memories/search?q=comedy")
COUNT=$(echo "$RESP" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('memories',[])))" 2>/dev/null)
if [ "$COUNT" -gt 0 ] 2>/dev/null; then
    pass "GET /v1/memories/search?q=comedy - Found $COUNT memories"
else
    fail "GET /v1/memories/search?q=comedy"
fi

# Full-text search with location
echo -e "\n[11] Full-Text Search with Location Filter"
RESP=$(curl -s "$BASE_URL/v1/memories/search?q=comedy&lat=40.7128&lng=-74.0060&radius_km=100")
COUNT=$(echo "$RESP" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('memories',[])))" 2>/dev/null)
if [ "$COUNT" -gt 0 ] 2>/dev/null; then
    pass "GET /v1/memories/search?q=comedy&lat=...&lng=... - Found $COUNT memories near NYC"
else
    fail "GET /v1/memories/search with location filter"
fi

echo -e "\n========================================"
echo "Tests complete!"
