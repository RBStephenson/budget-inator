# The Budget-inator

[![CI](https://github.com/RBStephenson/budget-inator/actions/workflows/ci.yml/badge.svg)](https://github.com/RBStephenson/budget-inator/actions/workflows/ci.yml)
[![Build Check](https://github.com/RBStephenson/budget-inator/actions/workflows/build-check.yml/badge.svg)](https://github.com/RBStephenson/budget-inator/actions/workflows/build-check.yml)
[![Release](https://github.com/RBStephenson/budget-inator/actions/workflows/release.yml/badge.svg)](https://github.com/RBStephenson/budget-inator/actions/workflows/release.yml)
[![CodeQL](https://github.com/RBStephenson/budget-inator/actions/workflows/codeql.yml/badge.svg)](https://github.com/RBStephenson/budget-inator/actions/workflows/codeql.yml)
&nbsp;
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)

A personal budget management application that helps you track bills against your pay schedule — so you always know which bills land in which pay period, and you never get caught off guard by a due date.

## Features

**Dashboard**
- Toggle between **By Pay Period** and **By Month** views
- Current pay period shown as a hero card; upcoming periods listed below
- Stat cards for available cash, bills due, late flags, and paid progress
- **Buffer balance** stat — running total carried from every already-closed pay period, tracked independently of the live current-period balance
- Quick Add for fast monthly bills, with a link to the full bill form
- Bills grouped by category within each period, with per-category subtotals
- Running balance showing the **available-to-spend** amount (green ≥ 20%, amber < 20%, red = overspent)
- **Paid so far / Still to pay** breakdown on each period card
- Sticky **flagged bills banner** when any bill cannot be paid on time
- **Late-bill count badge** on the sidebar Dashboard link, so flagged bills are visible without opening the dashboard
- **Pay date override** — adjust the pay date on any individual period
- **Bill move/reset** — move one unpaid bill occurrence to another pay date, then reset it when needed
- **Mark bills paid, skipped, or pending** inline on the dashboard, individually or **all at once** with the period's "Mark all paid" button
- **Keyboard shortcut** — press "P" on a focused bill row to mark it paid
- **Variable bill actuals** — enter the real amount for variable bills directly on the period card
- **Payday actuals** — save the actual deposit or current balance after payday to re-anchor projections
- **Starting balance edits** directly on period cards
- **Rebalance available funds** — preview and apply moves that pull eligible future bills into a paycheck with leftover cash
- **Past periods** — expand completed periods to review and retroactively mark missed payments
- Unpaid bills from a previous period show in the current period only, with the original due date preserved and no duplicate total

**Bill management**
- Add bills with Quick Add or the full bill form; edit, duplicate, and deactivate existing bills
- Effective-dated edits preserve historical bill names, amounts, categories, and due rules
- **Payment history** — the edit form has a collapsible section showing every past instance of a bill (due date, status, estimated/actual amount, paid date), read-only
- Search, category-filter, sort by name or annual cost, and optionally show inactive bills
- Sinking funds reserve part of each paycheck for large future bills
- Recurrences: Monthly, Bi-weekly, Weekly, Quarterly, Semi-annual, Annual, One-time
- Categories: Housing, Utilities, Subscriptions, Insurance, Debt, Savings, Other
- Optional **grace period** — how many days after the due date you can still pay without being late
- **Variable flag** — marks bills whose amount changes each cycle
- Optional bill notes are saved with the bill and included in backups, with a hover/focus tooltip on the dashboard row

**Reports & exports**
- **Annual cost breakdown** — modal showing per-payment and annual cost for every active bill, grouped by category with subtotals, plus a donut chart with a color/percentage legend
- **PDF report** — downloadable budget report covering the pay period schedule and a monthly income/bills/sinking-fund/net summary
- **JSON backup** — export and import your full data set, including effective-dated bill history, payment history, adjusted pay dates, and payday actuals; import previews the file's contents (or validation errors) before overwriting anything; delete all data and start fresh

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | Python 3.12 + FastAPI |
| Frontend | React 19 + TypeScript + Vite |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Testing | pytest (backend) + Vitest (frontend) |
| Packaging | PyInstaller — single-file Windows & Linux executables |

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
│   │   └── api/      # API client
│   └── tests/
├── packaging/        # PyInstaller spec and standalone entry point
└── .github/          # CI/CD and repo config
```

See [docs/user-guide.md](docs/user-guide.md) for a full walkthrough of every feature.

## Getting Started

### Standalone (recommended for most users — no Docker needed)

1. Go to the [Releases page](https://github.com/RBStephenson/budget-inator/releases) and download the file for your OS:
   - **Windows**: `budget-inator-windows.exe`
   - **Linux**: `budget-inator-linux`

2. Run the file. Your browser will open automatically to `http://localhost:8585`.

3. Open **Settings**, enter your pay schedule (net salary, frequency, first paycheck date), then add your bills.

Your budget database is stored in your user data folder and survives app updates:
- **Windows**: `%LOCALAPPDATA%\Budget-inator\`
- **Linux**: `~/.local/share/Budget-inator/`

> macOS builds aren't published yet — use Docker or the manual setup below.

---

### Docker

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

**Production:**
```bash
docker compose up
```
Open [http://localhost:8090](http://localhost:8090).

**Development** (backend hot-reload on save):
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

The SQLite database is stored in `./data/budget.db` (created automatically).
Docker Compose checks the backend's `/health` endpoint and reports the service as
unhealthy if the API stops responding.

#### Backend configuration

For manual backend runs, copy `backend/.env.example` to `backend/.env` and adjust
these settings as needed. Docker Compose supplies both values automatically.

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./budget.db` | SQLAlchemy connection string for the budget database |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | JSON array of frontend origins allowed to call the API |

The backend writes one JSON log entry per completed or failed request. Request logs
include the method, path, status, and duration, but never include query strings,
headers, or request bodies.

**E2E tests** (Playwright, isolated stack — never touches `./data/budget.db`):
```bash
docker compose -f docker-compose.yml -f docker-compose.e2e.yml -p budget-inator-e2e up -d
npm run test:e2e --prefix frontend
docker compose -p budget-inator-e2e down -v   # -v drops the throwaway DB volume
```
Runs on its own ports (8091/8002/5175) and its own Compose project, so it's safe to run alongside the stack above. See `docker-compose.e2e.yml` for details.

---

### Manual setup (without Docker)

#### Prerequisites
- Python 3.12+
- Node.js 22+

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
