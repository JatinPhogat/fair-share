# Fair Share

Shared expense management app for groups — track, split, and settle expenses with CSV import and anomaly detection.

Built for a flat of roommates dealing with messy shared expense data: inconsistent names, duplicate entries, multi-currency transactions, and members joining/leaving over time.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 6.0 + Django REST Framework |
| Frontend | React 19 (Vite) |
| Auth | JWT via SimpleJWT |
| Database | SQLite (relational, as required) |
| Import | openpyxl + custom anomaly detection engine |

## Features

- **User auth** — Register, login, JWT token management
- **Groups** — Create groups with time-aware membership (join/leave dates)
- **Expenses** — CRUD with 4 split types: equal, unequal, percentage, share
- **Multi-currency** — USD expenses converted to INR at configurable exchange rate
- **Balances** — Per-member balance breakdown (paid vs owed)
- **Debt simplification** — Greedy algorithm to minimize settlement transactions
- **CSV/XLSX import** — Upload → anomaly detection → user review → commit workflow
- **Anomaly detection** — 14 anomaly types including duplicates, settlements, name variants, date errors, membership violations

## Setup

### Backend

```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server proxies `/api` requests to Django at `localhost:8000`.

## API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | Register new user |
| POST | `/api/auth/login/` | Get JWT token pair |
| POST | `/api/auth/refresh/` | Refresh access token |
| GET | `/api/auth/profile/` | Current user info |

### Groups & Expenses
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/groups/` | List/create groups |
| GET/PUT/DELETE | `/api/groups/{id}/` | Group detail |
| POST | `/api/groups/{id}/add-member/` | Add member to group |
| GET | `/api/groups/{id}/balances/` | Member balance summary |
| GET | `/api/groups/{id}/debts/` | Simplified debt settlements |
| GET/POST | `/api/groups/{id}/expenses/` | List/create expenses |
| GET/POST | `/api/groups/{id}/payments/` | List/create payments |

### Import
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/import/upload/` | Upload CSV/XLSX, parse and detect anomalies |
| GET | `/api/import/{id}/` | Get import session with rows and anomalies |
| PATCH | `/api/import/{id}/rows/{row_id}/` | Resolve row (approve/skip) |
| POST | `/api/import/{id}/commit/` | Commit reviewed import to expenses |

## Project Structure

```
fair-share/
├── accounts/          # User model, auth serializers/views
├── expenses/          # Group, Expense, Payment models + balance engine
│   ├── models.py      # Group, GroupMembership, Expense, ExpenseSplit, Payment
│   ├── balance.py     # Balance calculation + debt simplification
│   ├── views.py       # API viewsets
│   └── serializers.py
├── importer/          # CSV/XLSX import with anomaly detection
│   ├── parser.py      # Anomaly detection engine (14 types)
│   ├── views.py       # Upload/review/commit workflow
│   └── models.py      # ImportSession, ImportRow, ImportAnomaly
├── core/              # Django project settings
├── frontend/          # React app (Vite)
│   └── src/pages/     # Login, Register, Dashboard, GroupDetail
├── SCOPE.md           # Anomaly log + database schema
├── DECISIONS.md       # Engineering decision log
└── AI_USAGE.md        # AI tools used + error cases
```

## AI Tools

Built with Gemini as development collaborator. See [AI_USAGE.md](AI_USAGE.md) for details including three cases where the AI produced incorrect output and how they were caught and fixed.
