"""Write a due-soon bill digest to a file (BI-75).

    python -m app.digest --db path/to/budget.db --out bills-due.md [--days 3]

Opens the database read-only, runs the schedule engine, and writes a short
markdown digest of the bills due soon (see ``app.services.due_soon``). Built for
a local scheduled job that cannot reach the running app: the job runs this
first, then reads the file.

On any failure it still writes the output file, marked ``status: error``, and
exits non-zero, so a reader sees the failure instead of yesterday's list.
"""

from __future__ import annotations

import argparse
import sys
import traceback
from collections.abc import Sequence
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.services.due_soon import (
    DEFAULT_WINDOW_DAYS,
    MAX_WINDOW_DAYS,
    render_error,
    render_markdown,
    select_due_soon,
)
from app.services.schedule_service import build_schedule

EXIT_OK = 0
EXIT_FAILED = 1

# The longest pay period (monthly) spans at most 31 days, so fetching this far
# ahead lets a payday see its whole period.
PAY_PERIOD_SPAN_DAYS = 31

# A bill can be assigned to a paycheck well before its due date (paid early,
# or moved there), and the engine carries an unpaid bill forward only one
# period. So fetch a year back, matching the engine's own 365-day carry
# look-back, or such a bill has no copy in the fetched periods at all.
LOOKBACK_DAYS = 365


def _window_days(value: str) -> int:
    days = int(value)
    if not 0 <= days <= MAX_WINDOW_DAYS:
        raise argparse.ArgumentTypeError(f"must be between 0 and {MAX_WINDOW_DAYS}")
    return days


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m app.digest",
        description="Write a markdown digest of the bills due soon.",
    )
    parser.add_argument("--db", type=Path, required=True, help="path to budget.db")
    parser.add_argument("--out", type=Path, required=True, help="file to write")
    parser.add_argument(
        "--days",
        type=_window_days,
        default=DEFAULT_WINDOW_DAYS,
        help=f"days ahead to include (default {DEFAULT_WINDOW_DAYS})",
    )
    return parser.parse_args(argv)


def _read_only_engine(db_path: Path) -> Engine:
    # mode=ro makes SQLite itself refuse writes, so this command cannot change
    # the user's data even if the engine ever tried to.
    url = f"sqlite:///file:{db_path.resolve().as_posix()}?mode=ro&uri=true"
    return create_engine(url)


def _write_atomically(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def build_digest_text(db_path: Path, today: date, window_days: int) -> str:
    if not db_path.is_file():
        raise FileNotFoundError(f"Database not found: {db_path}")
    fetch_from = today - timedelta(days=LOOKBACK_DAYS)
    fetch_to = today + timedelta(days=max(window_days, PAY_PERIOD_SPAN_DAYS))
    engine = _read_only_engine(db_path)
    try:
        with Session(engine) as db:
            schedule = build_schedule(db, fetch_from, fetch_to)
    finally:
        engine.dispose()
    return render_markdown(select_due_soon(schedule.periods, today, window_days))


def main(argv: Sequence[str] | None = None, today: date | None = None) -> int:
    args = _parse_args(argv)
    run_date = today or date.today()  # local date, matching the rest of the app
    try:
        text = build_digest_text(args.db, run_date, args.days)
    except Exception as exc:  # noqa: BLE001 - reported in the file and on stderr
        traceback.print_exc(file=sys.stderr)
        _write_atomically(
            args.out, render_error(run_date, f"{type(exc).__name__}: {exc}")
        )
        return EXIT_FAILED
    _write_atomically(args.out, text)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
