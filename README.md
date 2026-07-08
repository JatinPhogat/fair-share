# Fair Share

Shared expense management platform for groups — track, split, and settle expenses with intelligent data import and anomaly detection.

## Tech Stack

- **Backend**: Django 5.1 + Django REST Framework
- **Auth**: JWT via SimpleJWT
- **Database**: SQLite (dev) / PostgreSQL (production)
- **Config**: django-environ for 12-factor app compliance

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | Register |
| POST | `/api/auth/login/` | JWT token pair |
| POST | `/api/auth/refresh/` | Refresh token |
| GET | `/api/auth/profile/` | Current user |

## Roadmap

- [ ] Group management with time-aware membership
- [ ] Multi-currency expense tracking with split types
- [ ] CSV/XLSX import with anomaly detection engine
- [ ] Debt simplification via min-transaction algorithm
- [ ] React frontend
- [ ] Production deployment

## AI Tools

Built with Gemini as development collaborator. See `AI_USAGE.md` for details.
