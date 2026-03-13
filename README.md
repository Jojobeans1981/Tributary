# TRIBUTARY

Community matching platform for K-12 literacy professionals.

**Client:** Upstream Literacy
**Phase:** 1 of 4 — Foundation

## Stack

- **Backend:** Python 3.11+ · Django 4.2 LTS · Django REST Framework · Celery · Redis
- **Frontend:** Next.js 14+ (App Router, TypeScript strict) · Tailwind CSS 3+
- **Database:** PostgreSQL 15+
- **Hosting:** Render (Daphne ASGI)

## Local Development

1. Copy `.env.example` to `.env` and fill in values
2. `cd tributary_api && pip install -r requirements/dev.txt`
3. `python manage.py migrate`
4. `python manage.py createsuperuser`
5. `python manage.py runserver`

Frontend:
1. `cd tributary_web && npm install`
2. `npm run dev`
