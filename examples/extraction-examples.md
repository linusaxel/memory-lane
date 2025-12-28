# Extraction Examples

Input/output pairs demonstrating expected LLM behavior.

---

## Example 1: Clear venue mention (HIGH confidence)

**Input:**
```
[145.2] Last time I was in Paris, I had the most incredible
[148.0] croissant at this little place called Du Pain et des Idees
[152.3] It's in the 10th arrondissement, near Canal Saint-Martin
[156.1] I remember sitting outside watching people walk by
```

**Expected output:**
```json
{
  "memories": [{
    "place_name": "Du Pain et des Idees, Paris",
    "place_query": "Du Pain et des Idees bakery 10th arrondissement Paris France",
    "timestamp_start": 148.0,
    "summary": "The host recalls having an incredible croissant at Du Pain et des Idees, a bakery in Paris's 10th arrondissement near Canal Saint-Martin. They remember sitting outside and watching people walk by.",
    "tags": ["food", "travel"],
    "location_precision": "exact",
    "confidence": "high"
  }]
}
```

---

## Example 2: Neighborhood-level (MEDIUM confidence)

**Input:**
```
[302.5] When I lived in Tokyo, I used to wander around
[305.0] Shimokitazawa on weekends. There's just this amazing
[308.2] energy there, all these vintage shops and live music venues
[312.1] I found my favorite leather jacket there
```

**Expected output:**
```json
{
  "memories": [{
    "place_name": "Shimokitazawa, Tokyo",
    "place_query": "Shimokitazawa neighborhood Tokyo Japan",
    "timestamp_start": 305.0,
    "summary": "The host describes regularly exploring Shimokitazawa when they lived in Tokyo. They loved the neighborhood's energy, vintage shops, and live music venues, and found their favorite leather jacket there.",
    "tags": ["travel", "culture"],
    "location_precision": "neighborhood",
    "confidence": "medium"
  }]
}
```

---

## Example 3: No memories (empty result)

**Input:**
```
[50.0] I've always wanted to visit Japan
[52.5] Everyone says the food is amazing there
[55.0] Maybe next year I'll finally make the trip
```

**Expected output:**
```json
{
  "memories": []
}
```

**Rationale:** Hypothetical future travel, no specific place, nothing happened yet.

---

## Example 4: Multiple memories in one chunk

**Input:**
```
[200.0] So our first stop was the Louvre. We spent three hours
[203.2] just in the Egyptian wing, it was incredible
[207.0] Then we walked along the Seine to Shakespeare and Company
[210.5] I bought a first edition there, signed by the author
[214.0] We ended the day at a tiny wine bar near Saint-Germain
[217.3] I don't remember the name but the owner recommended
[220.1] this amazing Burgundy
```

**Expected output:**
```json
{
  "memories": [
    {
      "place_name": "The Louvre, Egyptian Wing",
      "place_query": "Louvre Museum Egyptian antiquities Paris France",
      "timestamp_start": 200.0,
      "summary": "The host describes spending three hours exploring the Egyptian wing of the Louvre, describing it as incredible.",
      "tags": ["culture", "art", "travel"],
      "location_precision": "exact",
      "confidence": "high"
    },
    {
      "place_name": "Shakespeare and Company, Paris",
      "place_query": "Shakespeare and Company bookstore Paris France",
      "timestamp_start": 207.0,
      "summary": "The host walked along the Seine to the famous Shakespeare and Company bookstore, where they purchased a signed first edition book.",
      "tags": ["culture", "travel"],
      "location_precision": "exact",
      "confidence": "high"
    },
    {
      "place_name": "Wine bar near Saint-Germain, Paris",
      "place_query": "wine bar Saint-Germain-des-Pres Paris France",
      "timestamp_start": 214.0,
      "summary": "The host ended their day at a small wine bar near Saint-Germain where the owner recommended an excellent Burgundy wine.",
      "tags": ["food", "nightlife", "travel"],
      "location_precision": "neighborhood",
      "confidence": "low"
    }
  ]
}
```

**Note:** The wine bar has low confidence because the name isn't known—it may not geocode well and would be filtered out.
