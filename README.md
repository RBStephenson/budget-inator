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
