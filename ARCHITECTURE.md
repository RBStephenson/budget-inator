# Budget-inator — Technical Summary

Personal budget management app that tracks bills against your pay schedule —
so you always know which bills land in which pay period and never get
caught off guard by a due date. Ships standalone (PyInstaller executable,
Windows/Linux), via Docker, or as a manual dev setup.

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic (schema migrations), Uvicorn |
| Database | SQLite (dev/standalone) / PostgreSQL (prod/Docker) |
| Frontend | React 19, TypeScript, Vite |
| Reports | ReportLab (server-generated PDF budget reports) |
| Packaging | PyInstaller — single-file Windows & Linux executables |
| Testing | pytest (backend) + Vitest (frontend) |
| CI/CD | GitHub Actions — CI (lint/typecheck/tests), CodeQL, cross-platform build-check, tagged release pipeline |

## Architecture

**Backend** (`backend/app/`) is a FastAPI app organized by concern:

- `api/` — route handlers: `bills`, `bill_instances`, `pay_schedule`,
  `pay_period_overrides`, `pay_period_actuals`, `reports`, `schedule`,
  `data` (backup/restore/export), `health`
- `models/` — SQLAlchemy ORM: `bill`, `bill_version` (effective-dated bill
  history), `bill_instance` (a bill's occurrence in a specific pay period),
  `pay_schedule`, `pay_period_override`, `pay_period_actual`, `enums`
- `schemas/` — Pydantic request/response models
- `services/` — business logic: `pay_period_engine` (the core scheduling
  logic that maps bills onto pay periods), `bill_versions` (effective-dated
  edit handling), `schedule_service`, `report_service` /`pdf_report`
  (ReportLab PDF generation)

Bills are **effective-dated**: editing a bill's name, amount, category, or
due rule doesn't rewrite history — it creates a new `bill_version` so past
periods still show what was actually true at the time. `bill_instance` rows
tie a bill (and its applicable version) to a specific occurrence in a pay
period, tracking paid/skipped/pending status and (for variable bills) the
actual amount.

**Database**: SQLite for standalone/dev, PostgreSQL for the Docker
production compose. Alembic manages schema migrations.

**Frontend** (`frontend/src/`): React SPA — `pages/` per route (routed via
`router.ts`), `components/` for shared UI, `context/` for cross-cutting
state, `hooks/`, `api/` for the typed HTTP client. No heavy state-management
library — the app is small enough to lean on local/context state plus
direct API calls.

**Packaging** (`packaging/`): `standalone.py` is the PyInstaller entry point
that boots the FastAPI backend and opens the browser to it automatically;
`budget-inator.spec` defines the PyInstaller build. Produces a single
`.exe` (Windows) or binary (Linux) with no separate install step.

## Core domain concepts

- **Pay schedule** — net salary, pay frequency, first paycheck date; drives
  every period calculation
- **Pay period** — a single pay-to-pay window; the dashboard's primary unit
- **Bill** — recurring or one-time expense with a category, recurrence rule
  (monthly/bi-weekly/weekly/quarterly/semi-annual/annual/one-time), optional
  grace period, and an optional **variable** flag (amount differs per cycle)
- **Sinking fund** — a bill-like reservation that sets aside part of each
  paycheck toward a future large expense
- **Bill instance** — one occurrence of a bill in one pay period; carries
  paid/skipped/pending state and (for variable bills) the actual amount paid
- **Pay period override** — an adjusted pay date or actual deposit amount
  for a specific period, used to re-anchor projections to reality

## Release & versioning

Tag-triggered release pipeline (mirrors STL Studio's): pushing a version tag
builds the PyInstaller executables for Windows and Linux and publishes a
GitHub Release. `build-check.yml` validates cross-platform builds
independently of releases; `ci.yml` runs lint/typecheck/tests on every push;
`codeql.yml` runs security scanning.

## Testing & quality gates

- Backend: pytest
- Frontend: Vitest
- CodeQL security scanning on every push
- Cross-platform build-check workflow (Windows/Linux) separate from the
  release pipeline
