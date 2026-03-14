# TRIBUTARY Changelog

## Phase 1 — Foundation

- Custom `User` model with UUID primary key, role-based access (MEMBER, DISTRICT_ADMIN, UPSTREAM_STAFF, PLATFORM_ADMIN)
- JWT authentication with SimpleJWT (access + refresh tokens)
- Email registration with django-allauth email verification
- FERPA consent capture (version, IP, timestamp)
- Password reset flow (email link with uid/token)
- District model with NCES data fields (enrollment, FRL%, ELL%, locale type)
- District ETL management command for CSV ingestion with locale-type mapping
- User profile API (view, update with bio, district, name)
- `ok()` / `err()` response envelope utilities
- Split settings (base / dev / prod)
- `TrackingJWTAuthentication` for last_seen tracking via Redis

## Phase 2 — Matching Engine

- Problem statement taxonomy model (title, description, category, version, is_active)
- User problem selections with max-3 enforcement (model + view layers)
- Pairwise match scoring algorithm:
  - Demographic score (locale diversity, FRL gap, ELL gap)
  - Problem overlap score (shared selections)
  - Total score = demographic + problem
- `MatchScore` model with unique `(user_a, user_b)` pair (lexicographic UUID ordering)
- Match feed API with pagination, `min_score` filter, sorting
- Connection state machine: PENDING → ACCEPTED / DECLINED / BLOCKED
  - Requester creates, recipient decides
  - Block action available to either party
  - Duplicate prevention (no parallel PENDING/ACCEPTED)
- Blocked user exclusion from match feed
- Celery tasks: `compute_all_match_scores` (nightly), `compute_user_match_scores` (on selection change)

## Phase 3 — Messaging & Moderation

- Conversation model with participant tracking and `last_read_at` cursor
- Message model with soft-delete support (`is_deleted`, `deleted_by`)
- System messages for staff join events
- Real-time-ready message pagination (50 per page, cursor-based)
- Notification system with types: NEW_MESSAGE, CONNECTION_REQUEST, CONNECTION_ACCEPTED, STAFF_JOINED, FEEDBACK_PROMPT
- Human-readable notification messages
- Mark-all-read and per-conversation read tracking
- File upload endpoint with extension/size validation
- Staff moderation suite:
  - Join any conversation (system message + notifications)
  - Soft-delete messages (audit trail)
  - Direct message any member (creates staff-initiated conversation)
  - Broadcast to multiple recipients (rate-limited: 3/24h via Redis)
  - Suspend member accounts (cannot suspend staff/admin)
- `StaffAction` audit log for all moderation actions
- `IsUpstreamStaff` permission class
- Email preference model (IMMEDIATE / DAILY_DIGEST / OFF)
- Message email notifications with preference checking

## Phase 4 — Community, Analytics & Polish

### Community & Channels
- Community directory API with paginated member listing (24/page)
  - Search by name/district, filter by state/locale/problem
  - Sort by match score, name, or join date
  - Blocked user exclusion
- Channel system: active problem statements as browsable channels
  - Channel list with member counts
  - Channel member view sorted by match score
- Community and Channels frontend pages with member cards, connect actions

### Featured Members & Feedback
- `FeaturedMember` model (max 5 active, optional expiry date)
- Staff CRUD for featured members
- `MatchFeedback` model (1–5 rating, optional text, one per connection)
- Feedback submission with party validation and duplicate prevention
- Feedback prompt Celery task (7 days after first message)

### Staff Tools
- Taxonomy CRUD: create, edit (auto-version bump), retire problem statements
- Analytics dashboard API with date range filtering and 24h caching
  - Summary: total members, messages sent, match acceptance rate, avg feedback
  - Charts: member growth, message volume, problem distribution, top district pairs
- CSV export endpoint (streaming, always fresh)
- Taxonomy and analytics frontend pages (staff-only)

### Performance
- N+1 query fixes in match feed (batch prefetch problem selections, consolidated blocked-ID queries)
- `select_related` on connection list queries
- 9 database indexes across Connection, Message, Notification, and User models

### Accessibility (WCAG 2.1 AA)
- Skip-to-content link on all pages
- `aria-label`, `aria-expanded`, `aria-haspopup` on all interactive elements
- `role="banner"`, `role="menu"`, `role="menuitem"`, `role="dialog"`, `aria-modal` semantics
- Focus ring styles on all interactive elements
- Escape key handler for dropdown/mobile drawer
- `role="progressbar"` with `aria-valuenow/min/max` on profile completion

### Profile Completion
- Completion formula: bio(40%) + district(30%) + 1 selection(20%) + 2 selections(10%)
- Dashboard checklist UI with per-item progress and links
- Profile completion percentage in user serializer

### Celery Beat Schedule
- `daily-analytics-cache` — 01:00 UTC
- `nightly-match-scores` — 02:00 UTC
- `daily-digest-emails` — 07:00 UTC
- `daily-profile-nudge` — 10:00 UTC (incomplete profiles >7 days old, one-time)
