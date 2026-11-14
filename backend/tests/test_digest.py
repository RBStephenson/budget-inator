"""End-to-end tests for the `python -m app.digest` command (BI-75).

These use a real SQLite file, because the command's job is to open one
read-only and run the real schedule engine against it.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.database import Base
from app.digest import EXIT_FAILED, EXIT_OK, _read_only_engine, main
from app.models import Bill, BillInstance, PayPeriodOverride, PaySchedule
from app.services import schedule_service

TODAY = date(2026, 11, 14)  # a Saturday; biweekly paydays below fall on Fridays


def _make_db(path: Path, with_schedule: bool = True) -> None:
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        if with_schedule:
            db.add(
                PaySchedule(
                    net_salary="2000.00",
                    first_paycheck_date=date(2026, 1, 2),
                    beginning_balance="500.00",
                    frequency="biweekly",
                )
            )
        for name, due_day in [("Internet", 15), ("Rent", 1), ("Water", 16)]:
            db.add(
                Bill(
                    name=name,
                    estimated_amount="100.00",
                    recurrence="monthly",
                    due_day=due_day,
                    grace_period_days=0,
                    category="other",
                    is_variable=False,
                    is_active=True,
                )
            )
        db.commit()
        water = db.query(Bill).filter_by(name="Water").one()
        db.add(
            BillInstance(
                bill_id=water.id,
                due_date=date(2026, 11, 16),
                estimated_amount="100.00",
                status="paid",
            )
        )
        db.commit()
    engine.dispose()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "budget.db"
    _make_db(path)
    return path


def test_writes_the_digest_from_the_real_engine(db_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "bills-due.md"

    code = main(["--db", str(db_path), "--out", str(out)], today=TODAY)

    assert code == EXIT_OK
    body = out.read_text(encoding="utf-8")
    assert body.startswith("generated: 2026-11-14\nstatus: ok\n")
    # Biweekly paydays from Jan 2 put Nov 15 and Nov 16 on the Nov 6 paycheck.
    assert "- Due Sun Nov 15: Internet, $100.00 (pay on Fri Nov 06)" in body
    assert "- Due Mon Nov 16: Water, $100.00 (pay on Fri Nov 06, marked paid)" in body
    assert "Rent" not in body  # due on the 1st, outside the 3-day window


def _freeze_engine_clock(monkeypatch: pytest.MonkeyPatch, day: date) -> None:
    # The engine picks the period that carried bills land in from its own
    # date.today(), so pin it to match the injected digest date.
    class _Frozen(date):
        @classmethod
        def today(cls) -> date:  # type: ignore[override]
            return day

    monkeypatch.setattr(schedule_service, "date", _Frozen)


@pytest.fixture
def engine_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    _freeze_engine_clock(monkeypatch, TODAY)


def _add_bill_with_instance(
    db_path: Path,
    name: str,
    due: date,
    status: str,
    manual_pay_date: date | None = None,
    paid_at: datetime | None = None,
) -> None:
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    with Session(engine) as db:
        bill = Bill(
            name=name,
            estimated_amount="50.00",
            recurrence="monthly",
            due_day=due.day,
            grace_period_days=0,
            category="other",
            is_variable=False,
            is_active=True,
        )
        db.add(bill)
        db.commit()
        db.add(
            BillInstance(
                bill_id=bill.id,
                due_date=due,
                estimated_amount="50.00",
                status=status,
                manual_pay_date=manual_pay_date,
                paid_at=paid_at,
            )
        )
        db.commit()
    engine.dispose()


@pytest.mark.usefixtures("engine_clock")
def test_lists_an_unmarked_bill_moved_to_a_far_earlier_paycheck(
    db_path: Path, tmp_path: Path
) -> None:
    # Moved to the Sep 25 paycheck, four periods back, and never marked. The
    # engine carries unpaid bills forward only one period, so this bill exists
    # only in that old period; the digest must fetch back far enough to see it.
    _add_bill_with_instance(
        db_path, "Phone", date(2026, 11, 17), "pending", date(2026, 9, 25)
    )
    out = tmp_path / "bills-due.md"

    main(["--db", str(db_path), "--out", str(out)], today=TODAY)

    assert "- Due Tue Nov 17: Phone, $50.00 (pay on Fri Sep 25)" in out.read_text(
        encoding="utf-8"
    )


def test_payday_lists_bills_assigned_to_that_paycheck(
    db_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Due Dec 2 (the Nov 20 paycheck's period) but moved to the Nov 6
    # paycheck: it belongs on Nov 6's payday list, not Nov 20's.
    _add_bill_with_instance(
        db_path, "Moved bill", date(2026, 12, 2), "pending", date(2026, 11, 6)
    )
    out = tmp_path / "bills-due.md"

    _freeze_engine_clock(monkeypatch, date(2026, 11, 6))
    main(["--db", str(db_path), "--out", str(out)], today=date(2026, 11, 6))
    nov_6 = out.read_text(encoding="utf-8")

    _freeze_engine_clock(monkeypatch, date(2026, 11, 20))
    main(["--db", str(db_path), "--out", str(out)], today=date(2026, 11, 20))
    nov_20 = out.read_text(encoding="utf-8")

    assert "Payday (Fri Nov 06)" in nov_6
    assert "- Due Wed Dec 02: Moved bill, $50.00\n" in nov_6
    assert "- Due Sun Nov 15: Internet, $100.00\n" in nov_6
    # Rent (Nov 1) and the moved bill's Nov 2 occurrence sit on the Oct 23
    # paycheck, unmarked, so the engine carries them in: counted, not listed.
    assert "2 bills from earlier paychecks aren't marked paid" in nov_6
    assert "Rent" not in nov_6
    assert "Payday (Fri Nov 20)" in nov_20
    assert "Moved bill" not in nov_20


def test_payday_moved_earlier_lists_the_whole_period(
    db_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Holiday case through the real engine: the Nov 20 paycheck moved to
    # Nov 19. The period itself still starts Nov 20, so with --days 0 the
    # digest must look ahead to find the payday period at all.
    early_payday = date(2026, 11, 19)
    _freeze_engine_clock(monkeypatch, early_payday)
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    with Session(engine) as db:
        db.add(
            PayPeriodOverride(
                original_pay_date=date(2026, 11, 20),
                overridden_pay_date=early_payday,
            )
        )
        db.commit()
    engine.dispose()
    _add_bill_with_instance(db_path, "Late in period", date(2026, 12, 2), "pending")
    out = tmp_path / "bills-due.md"

    main(["--db", str(db_path), "--out", str(out), "--days", "0"], today=early_payday)

    body = out.read_text(encoding="utf-8")
    assert "Payday (Thu Nov 19)" in body
    assert "- Due Wed Dec 02: Late in period, $50.00\n" in body


@pytest.mark.usefixtures("engine_clock")
def test_lists_a_bill_paid_early_in_an_earlier_period(
    db_path: Path, tmp_path: Path
) -> None:
    # Paid on Oct 25, so the engine files it under that earlier paycheck and
    # does not carry it; only fetching back from today finds it.
    _add_bill_with_instance(
        db_path,
        "Insurance",
        date(2026, 11, 17),
        "paid",
        paid_at=datetime(2026, 10, 25, 12, 0),
    )
    out = tmp_path / "bills-due.md"

    main(["--db", str(db_path), "--out", str(out)], today=TODAY)

    # Paid on Oct 25, so its Pay on is the Oct 23 paycheck it was paid from.
    assert (
        "- Due Tue Nov 17: Insurance, $50.00 (pay on Fri Oct 23, marked paid)"
        in out.read_text(encoding="utf-8")
    )


def test_days_option_widens_the_window(db_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "bills-due.md"

    main(["--db", str(db_path), "--out", str(out), "--days", "20"], today=TODAY)

    assert "Rent" in out.read_text(encoding="utf-8")  # Dec 1 is within 20 days


def test_never_modifies_the_database(db_path: Path, tmp_path: Path) -> None:
    before = _sha256(db_path)

    main(["--db", str(db_path), "--out", str(tmp_path / "out.md")], today=TODAY)

    assert _sha256(db_path) == before
    assert not db_path.with_name("budget.db-journal").exists()


def test_session_refuses_writes(db_path: Path) -> None:
    with (
        Session(_read_only_engine(db_path)) as db,
        pytest.raises(OperationalError, match="readonly"),
    ):
        db.execute(text("DELETE FROM bills"))


def test_missing_database_writes_an_error_file_and_fails(tmp_path: Path) -> None:
    out = tmp_path / "bills-due.md"
    out.write_text(
        "generated: 2026-11-13\nstatus: ok\n\nyesterday's list\n", encoding="utf-8"
    )

    code = main(["--db", str(tmp_path / "nope.db"), "--out", str(out)], today=TODAY)

    assert code == EXIT_FAILED
    text = out.read_text(encoding="utf-8")
    assert text.startswith("generated: 2026-11-14\nstatus: error\n")
    assert "Database not found" in text
    assert "yesterday's list" not in text
    assert not (tmp_path / "nope.db").exists()  # read-only open must not create it


def test_no_pay_schedule_writes_an_error_file_and_fails(tmp_path: Path) -> None:
    path = tmp_path / "budget.db"
    _make_db(path, with_schedule=False)
    out = tmp_path / "bills-due.md"

    code = main(["--db", str(path), "--out", str(out)], today=TODAY)

    assert code == EXIT_FAILED
    assert "No pay schedule configured" in out.read_text(encoding="utf-8")


@pytest.mark.parametrize("days", ["-1", "32", "three"])
def test_rejects_a_bad_days_value(days: str, db_path: Path, tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(["--db", str(db_path), "--out", str(tmp_path / "o.md"), "--days", days])
