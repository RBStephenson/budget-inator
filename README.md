# The Budget-inator

[![CI](https://github.com/RBStephenson/budget-inator/actions/workflows/ci.yml/badge.svg)](https://github.com/RBStephenson/budget-inator/actions/workflows/ci.yml)
[![Build Check](https://github.com/RBStephenson/budget-inator/actions/workflows/build-check.yml/badge.svg)](https://github.com/RBStephenson/budget-inator/actions/workflows/build-check.yml)
[![Release](https://github.com/RBStephenson/budget-inator/actions/workflows/release.yml/badge.svg)](https://github.com/RBStephenson/budget-inator/actions/workflows/release.yml)
[![CodeQL](https://github.com/RBStephenson/budget-inator/actions/workflows/codeql.yml/badge.svg)](https://github.com/RBStephenson/budget-inator/actions/workflows/codeql.yml)
&nbsp;
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)

A personal budget management application that helps you track bills against your pay schedule — so you always know which bills land in which pay period, and you never get caught off guard by a due date.

## Features

**Dashboard**
- Toggle between **By Pay Period** and **By Month** views
- Current pay period shown as a hero card; upcoming periods listed below
- Bills grouped by category within each period, with per-category subtotals
- Running balance showing the **available-to-spend** amount (green ≥ 20%, amber < 20%, red = overspent)
- Sticky **flagged bills banner** when any bill cannot be paid on time
- **Pay date override** — adjust the pay date on any individual period
- **Mark bills paid, skipped, or pending** inline on the dashboard
- **Variable bill actuals** — enter the real amount for variable bills directly on the period card

**Bill management**
- Add, edit, and deactivate bills
- Effective-dated edits preserve historical bill names, amounts, categories, and due rules
- Sinking funds reserve part of each paycheck for large future bills
- Recurrences: Monthly, Bi-weekly, Weekly, Quarterly, Semi-annual, Annual, One-time
- Categories: Housing, Utilities, Subscriptions, Insurance, Debt, Savings, Other
- Optional **grace period** — how many days after the due date you can still pay without being late
- **Variable flag** — marks bills whose amount changes each cycle

**Reports & exports**
- **Annual cost breakdown** — modal showing per-payment and annual cost for every active bill, grouped by category with subtotals
- **PDF report** — downloadable budget report covering the pay period schedule and a monthly income/bills/net summary
- **JSON backup** — export and import your full data set, including bill history; delete all data and start fresh

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | Python 3.12 + FastAPI |
| Frontend | React 18 + TypeScript + Vite |
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
