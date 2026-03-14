# TRIBUTARY Issues Tracker

| ID | Phase | Description | Severity |
|----|-------|-------------|----------|
| 1 | 4 | Analytics `member_growth` chart queries DB per-day in a loop; could be slow for large date ranges | Low |
| 2 | 4 | Community directory loads all members into memory before paginating; switch to DB-level pagination at scale | Low |
| 3 | 4 | Match score sorting in community view is done in Python post-fetch; pre-join MatchScore in DB at scale | Low |
| 4 | 3 | Broadcast creates one conversation per recipient in a loop; use bulk_create for large lists | Low |
| 5 | 4 | FeaturedMember max-5 check has no transaction lock; possible race under concurrent staff requests | Low |
| 6 | 2 | Match score recompute is O(n²) for all active members; needs incremental approach at scale (>1k users) | Low |
| 7 | 4 | No WebSocket/SSE for real-time messaging; currently requires polling | Medium |
| 8 | 1 | No rate limiting on login/register endpoints; consider django-axes or DRF throttling | Medium |
