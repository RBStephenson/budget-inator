# The Budget-inator

A personal budget management application that helps you track bills against your pay schedule — so you always know which bills land in which pay period, and you never get caught off guard by a due date.

## Features

- **Pay schedule configuration** — enter your net salary and pay frequency (bi-weekly, semi-monthly, monthly, etc.)
- **Bill management** — track bills with amounts, due dates, recurrence (monthly, bi-weekly, quarterly, etc.), and optional grace periods
- **Pay period assignment** — automatically determines which bills are due in each pay period, paying early when needed to avoid being late
- **Late-payment flagging** — bills that cannot be covered before their due date are flagged prominently
- **Running balance** — see what remains after bills for each pay period

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | Python 3.12 + FastAPI |
| Frontend | React 18 + TypeScript + Vite |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Testing | pytest (backend) + Vitest (frontend) |

## Project Structure

```
budget-inator/
├── backend/          # FastAPI application
│   ├── app/
│   │   ├── api/      # Route handlers
│   │   ├── models/   # SQLAlchemy models
│   │   ├── schemas/  # Pydantic schemas
│   │   └── services/ # Business logic
│   └── tests/
├── frontend/         # React + Vite app
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── api/      # API client
│   └── tests/
└── .github/          # CI/CD and repo config
```

## Getting Started

### Docker (recommended)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

**Production:**
```bash
docker compose up
```
Open [http://localhost:8080](http://localhost:8080).

**Development** (backend hot-reload on save):
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

The SQLite database is stored in `./data/budget.db` (created automatically).

---

### Manual setup (without Docker)

#### Prerequisites
- Python 3.12+
- Node.js 20+

#### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Contributing

This is a personal project. See [SECURITY.md](SECURITY.md) for vulnerability reporting.

## License

MIT
