# TRIBUTARY

Community matching platform for K-12 literacy professionals.

**Client:** Upstream Literacy
**Phase:** 4 of 4 — Complete

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+ · Django 4.2 LTS · Django REST Framework · Celery · Redis |
| Frontend | Next.js 14+ (App Router, TypeScript strict) · Tailwind CSS 3+ |
| Database | PostgreSQL 15+ |
| Email | SendGrid transactional email |
| Hosting | Render (Daphne ASGI) |
| Auth | JWT (SimpleJWT) · django-allauth email verification |

## Architecture

```
tributary_api/                  # Django backend
├── apps/
│   ├── users/                  # Auth, registration, FERPA consent, profile, nudge tasks
│   ├── districts/              # NCES district data, ETL ingestion
│   ├── matching/               # Problem statements, selections, match scoring,
│   │                             connections, community directory, channels, feedback
│   ├── messaging/              # Conversations, messages, notifications, file uploads
│   └── staff/                  # Staff moderation, taxonomy CRUD, analytics, broadcasts
├── tributary_api/
│   └── settings/               # base / dev / prod split settings
└── manage.py

tributary_web/                  # Next.js frontend
├── app/
│   ├── login / register / verify-email / forgot-password
│   ├── onboarding/             # FERPA → district → problems wizard
│   ├── dashboard/              # Home with profile completion checklist
│   ├── profile/[id]/           # Public profile view + edit
│   ├── community/              # Paginated member directory
│   ├── channels/               # Problem-based channels with member lists
│   ├── matches/                # Match feed with connection actions
│   ├── inbox/                  # Conversations + real-time messaging
│   └── staff/                  # Analytics dashboard, taxonomy manager
├── lib/                        # api.ts, auth.ts utilities
└── tailwind.config.ts          # "Deep Water" palette
```

## Local Development

### Backend

```bash
cd tributary_api
cp .env.example .env            # Fill in values (see Environment Variables below)
pip install -r requirements/dev.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Frontend

```bash
cd tributary_web
npm install
npm run dev
```

### Celery (background tasks)

```bash
cd tributary_api
celery -A tributary_api worker --loglevel=info
celery -A tributary_api beat --loglevel=info
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Django secret key | `dev-insecure-key-change-me` |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | `localhost,127.0.0.1` |
| `DATABASE_URL` | PostgreSQL connection string | SQLite (dev) |
| `CELERY_BROKER_URL` | Redis URL for Celery | `redis://localhost:6379/0` |
| `SENDGRID_API_KEY` | SendGrid API key for transactional email | — |
| `DEFAULT_FROM_EMAIL` | From address for outbound email | — |
| `FRONTEND_URL` | Frontend base URL (for email links) | `http://localhost:3000` |
| `NEXT_PUBLIC_API_URL` | Backend API URL (frontend) | `http://localhost:8000` |

## Running Tests

```bash
cd tributary_api
pytest                          # All tests
pytest apps/users/              # Single app
pytest -v                       # Verbose output
```

## Celery Beat Schedule

| Task | Schedule | Description |
|------|----------|-------------|
| `daily-analytics-cache` | 01:00 UTC | Pre-compute analytics dashboard |
| `nightly-match-scores` | 02:00 UTC | Recompute all pairwise match scores |
| `daily-digest-emails` | 07:00 UTC | Send daily digest emails |
| `daily-profile-nudge` | 10:00 UTC | Nudge incomplete profiles (>7 days old) |
