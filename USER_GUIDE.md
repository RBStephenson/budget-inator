# Budget-inator — User Guide

A practical walkthrough for getting set up and using Budget-inator day to
day. For the exhaustive field-by-field reference, see
[docs/user-guide.md](docs/user-guide.md); for a quick feature list, see
[FEATURES.md](FEATURES.md).

## 1. Install

| Option | Best for |
|---|---|
| **Standalone** | Most people — single download, no Docker |
| **Docker** | Already running Docker, want the containerized/production setup |
| **Manual** | Development — running backend/frontend directly |

No prebuilt macOS build yet — use Docker or the manual setup on a Mac.

### Standalone

1. Go to [Releases](https://github.com/RBStephenson/budget-inator/releases)
   and download for your OS:
   - **Windows**: `budget-inator-windows.exe`
   - **Linux**: `budget-inator-linux`
2. Run it — your browser opens automatically to `http://localhost:8585`.

Your budget database lives in your user-data folder and survives updates:

| OS | Location |
|---|---|
| Windows | `%LOCALAPPDATA%\Budget-inator\` |
| Linux | `~/.local/share/Budget-inator/` |

### Docker

Requires Docker Desktop.

```bash
docker compose up
```

Open [http://localhost:8080](http://localhost:8080). For backend hot-reload
during development:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

The SQLite database is stored in `./data/budget.db`, created automatically.

### Manual (development)

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## 2. First-time setup

On first launch you'll see a welcome screen asking for your pay schedule.
Click **Set up pay schedule** (or go to **Settings**) and fill in:

| Field | What to enter |
|---|---|
| Net salary | Your take-home pay per paycheck |
| Pay frequency | Weekly, Bi-weekly, Semi-monthly, or Monthly |
| First paycheck date | Anchors every period calculation forward and backward |
| Current balance | What's in your account right now |

Save, then add your first bill with **+ Add Bill**.

## 3. Everyday workflow

### Check where you stand

The **Dashboard** is your home screen. The current pay period shows as a
hero card: opening balance, bills grouped by category with due dates and
statuses, and an **available-to-spend** figure color-coded green (healthy),
amber (under 20% left), or red (overspent). A **Buffer** stat card tracks
the running total carried from every already-closed pay period, separate
from the live current-period balance, and a **Paid so far / Still to pay**
breakdown shows how much of the period is already handled. A sticky banner
appears if any bill can't be paid on time, and the sidebar's Dashboard link
carries a badge with the current late-bill count so you can see it without
opening the page.

Switch to **By Month** for a calendar-level view — total income, total
bills, and net remaining per month, with red highlighting where bills
exceed income.

### Add and edit bills

Go to **Bills** (or click **+ Add Bill** from the dashboard). Add
recurring or one-time bills with a category, recurrence
(monthly/bi-weekly/weekly/quarterly/semi-annual/annual/one-time), optional
grace period, and — for bills whose amount changes each cycle — the
**variable** flag.

Editing a bill is **effective-dated**: past periods keep the old name/
amount/category/due rule, and only occurrences from the effective date
forward use your edit. To fix a single occurrence instead (this month's
amount, this month's status), use the controls on that bill's row on the
dashboard, not the bill form.

Need a similar bill (another streaming subscription, a second insurance
policy)? Click **Duplicate** on the Bills page to open the form pre-filled
with that bill's values (named "Copy of ..."). Saving creates a new,
independent bill — the original is untouched.

Check **Sinking fund** on a large infrequent bill (insurance, annual
subscription) to have Budget-inator reserve a slice of every paycheck
toward it ahead of time, instead of it hitting your balance as one lump sum.

### Track payments as they happen

On each bill's dashboard row: **✓ Paid**, **— Skip**, or **↺ Pending**.
These only affect that occurrence — not the bill's ongoing configuration.
With a bill row focused, pressing **P** marks it paid without reaching for
the mouse. To clear a whole period in one go, use **Mark all paid** on the
period card — it pays every remaining unpaid/late bill in that period at
once (skipped bills are left alone, since skipping is a deliberate choice).

- **Variable bill?** Click the (~)-prefixed amount to enter the real
  charge for that cycle; the period balance updates immediately.
- **Bill has notes?** A small indicator appears on its row — hover or
  focus it to read the note without opening the edit form.
- **Paycheck landed on a different date** (holiday, early deposit)? Use the
  pencil icon next to the pay date to override it for that period.
- Left something unpaid from a past period? It carries into the current
  period with an **Unpaid from previous period** badge — original due date
  preserved, no double-counting.

### Review spend and export

- **Annual Cost** modal: per-payment and annual cost for every active bill,
  grouped by category with subtotals — a quick gut-check on total yearly
  spend. A donut chart with a color/percentage legend breaks down annual
  spend by category at a glance.
- **Download PDF**: a report with the full pay-period schedule and a
  monthly income/bills/net summary, generated from current data.

### Back up your data

**Settings → Data management**:
- **Export backup** — a JSON file with your full pay schedule, bills,
  effective-dated history, payment statuses/actuals, and pay-date
  overrides. Keep it somewhere safe.
- **Import backup** — restores from a backup file. This **overwrites all
  current data** — it's for migration/recovery, not merging.
- **Delete all data** — wipes everything and returns to first-time setup.

## 4. Where to go next

- [docs/user-guide.md](docs/user-guide.md) — the full field-by-field
  reference, including every bill field, recurrence option, and settings
  detail
- [ARCHITECTURE.md](ARCHITECTURE.md) — technical overview if you're
  developing against the codebase
