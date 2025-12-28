# Testing Strategy

## Unit Tests

### Chunking
- Verify transcripts split correctly at time boundaries
- Confirm overlap behavior
- Test edge cases (empty transcripts, single segment)

### Merging
- Same place within 60s should merge
- Different places should not merge
- Time ranges should extend correctly
- Tags should deduplicate

## Integration Tests

### Full Pipeline Test
1. Ingest a single known-good video
2. Fetch transcript
3. Extract memories
4. Geocode places
5. Query API and verify results

## Extraction Quality Validation

Manual review process for spot-checking:
- Sample 20 recent extractions
- Rate each as good/bad/skip
- Track quality over time

### Quality Checklist
- Is the place real and identifiable?
- Does the summary accurately reflect the transcript?
- Is the timestamp correct?
- Are the tags appropriate?
- Is the confidence level accurate?

## Geocoding Validation

### Success Rate Query
```sql
SELECT
    geocode_status,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as pct
FROM places
GROUP BY geocode_status;
```

### Spot Check Coordinates
```sql
SELECT
    p.name,
    p.place_query,
    ST_Y(p.coordinates::geometry) as lat,
    ST_X(p.coordinates::geometry) as lng
FROM places p
WHERE geocode_status = 'success'
ORDER BY created_at DESC
LIMIT 20;
```

## Pipeline State Debugging

```bash
# Check pipeline progress
psql $DATABASE_URL -c "
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN transcript_fetched THEN 1 ELSE 0 END) as transcripts,
    SUM(CASE WHEN memories_extracted THEN 1 ELSE 0 END) as extracted
FROM content;
"

# Check geocoding status
psql $DATABASE_URL -c "
SELECT geocode_status, COUNT(*) FROM places GROUP BY geocode_status;
"

# Count memories
psql $DATABASE_URL -c "
SELECT COUNT(*) as memories FROM memories;
"

# Sample memories
psql $DATABASE_URL -c "
SELECT p.name, m.summary FROM memories m
JOIN places p ON m.place_id = p.id LIMIT 5;
"
```
