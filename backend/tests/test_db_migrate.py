"""Standalone database migration on startup (BI-68)."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from alembic import command
from app.db_migrate import (
    MigrationAction,
    UnrecognizedDatabaseError,
    migrate_database,
)
from app.models import Bill, BillInstance, BillVersion

ALEMBIC_DIR = Path(__file__).resolve().parent.parent / "alembic"
FIXED_NOW = datetime(2026, 10, 4, 11, 30, 0)
# Head of the migration chain at the v1.0.0 tag, read from the tag itself
# (git ls-tree v1.0.0 backend/alembic/versions). Deliberately not imported from
# app.db_migrate, so a wrong stamp revision there can't move the fixture too.
V1_0_0_HEAD = "c3d4e5f6a7b8"


def _url(db_path: Path) -> str:
    return f"sqlite:///{db_path.as_posix()}"


def _config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    return config


def _head() -> str | None:
    return ScriptDirectory.from_config(_config()).get_current_head()


def _upgrade_to(db_path: Path, revision: str) -> None:
    engine = create_engine(_url(db_path))
    with engine.begin() as connection:
        config = _config()
        config.attributes["connection"] = connection
        command.upgrade(config, revision)
    engine.dispose()


def _execute(db_path: Path, *statements: str) -> None:
    engine = create_engine(_url(db_path))
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
    engine.dispose()


def _revision(db_path: Path) -> str | None:
    engine = create_engine(_url(db_path))
    with engine.connect() as connection:
        revision = MigrationContext.configure(connection).get_current_revision()
    engine.dispose()
    return revision


def _tables(db_path: Path) -> set[str]:
    engine = create_engine(_url(db_path))
    tables = set(inspect(engine).get_table_names())
    engine.dispose()
    return tables


def _make_v1_standalone_db(db_path: Path) -> None:
    """A database shaped like one written by the v1.0.0 standalone exe.

    That build ran ``create_all`` and never wrote ``alembic_version``. Its
    schema was verified on 2026-10-04 to match the migrations at
    ``V1_0_0_HEAD`` (uniqueness on pay_period_overrides is an index
    there rather than a constraint; both enforce it), so migrating to that
    revision and dropping the version table reproduces it.
    """
    _upgrade_to(db_path, V1_0_0_HEAD)
    _execute(
        db_path,
        "DROP TABLE alembic_version",
        "INSERT INTO bills (name, estimated_amount, recurrence, due_day, "
        "category) VALUES ('Rent', 1500.00, 'monthly', 1, 'housing')",
        # bill_instances is rebuilt (copy, drop, recreate) by a later
        # migration, so it is the table whose rows are actually at risk.
        "INSERT INTO bill_instances (bill_id, due_date, estimated_amount, "
        "actual_amount, status, paid_at) VALUES (1, '2026-01-01', 1500.00, "
        "1480.00, 'paid', '2026-01-02 09:15:00')",
    )


def _backups(db_path: Path) -> list[Path]:
    return sorted(db_path.parent.glob(f"{db_path.stem}.backup-*"))


def test_fresh_database_is_built_by_migrations(tmp_path: Path) -> None:
    db_path = tmp_path / "budget.db"

    result = migrate_database(db_path, ALEMBIC_DIR, now=lambda: FIXED_NOW)

    assert result.action is MigrationAction.created
    assert result.backup_path is None
    assert _revision(db_path) == _head()
    assert _backups(db_path) == []


def test_v1_standalone_database_is_stamped_and_upgraded(tmp_path: Path) -> None:
    db_path = tmp_path / "budget.db"
    _make_v1_standalone_db(db_path)

    result = migrate_database(db_path, ALEMBIC_DIR, now=lambda: FIXED_NOW)

    assert result.action is MigrationAction.legacy_upgraded
    assert _revision(db_path) == _head()
    # The current models can read the user's data, so no "no such column".
    engine = create_engine(_url(db_path))
    with Session(engine) as session:
        bill = session.scalars(select(Bill)).one()
        assert (bill.name, str(bill.estimated_amount)) == ("Rent", "1500.00")
        assert bill.sinking_fund_enabled is False
        # The bill_versions migration backfilled the v1.0.0 bill's terms.
        version = session.scalars(select(BillVersion)).one()
        assert (version.bill_id, str(version.estimated_amount)) == (
            bill.id,
            "1500.00",
        )
        instance = session.scalars(select(BillInstance)).one()
        assert (
            instance.bill_id,
            instance.due_date,
            str(instance.actual_amount),
            instance.status,
            instance.paid_at,
        ) == (bill.id, date(2026, 1, 1), "1480.00", "paid", datetime(2026, 1, 2, 9, 15))
    engine.dispose()
    # The backup is the untouched v1.0.0 file.
    assert result.backup_path == tmp_path / "budget.backup-20261004-113000.db"
    assert _backups(db_path) == [result.backup_path]
    assert "alembic_version" not in _tables(result.backup_path)
    assert "pay_periods" in _tables(result.backup_path)


def test_database_at_head_is_left_alone_without_a_backup(tmp_path: Path) -> None:
    db_path = tmp_path / "budget.db"
    migrate_database(db_path, ALEMBIC_DIR, now=lambda: FIXED_NOW)
    before = db_path.read_bytes()

    result = migrate_database(db_path, ALEMBIC_DIR, now=lambda: FIXED_NOW)

    assert result.action is MigrationAction.up_to_date
    assert result.backup_path is None
    assert _backups(db_path) == []
    assert db_path.read_bytes() == before


def test_versioned_database_behind_head_is_backed_up_and_upgraded(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "budget.db"
    _upgrade_to(db_path, V1_0_0_HEAD)

    result = migrate_database(db_path, ALEMBIC_DIR, now=lambda: FIXED_NOW)

    assert result.action is MigrationAction.upgraded
    assert _revision(db_path) == _head()
    assert result.backup_path is not None
    assert _revision(result.backup_path) == V1_0_0_HEAD


def test_unversioned_database_not_shaped_like_v1_is_refused_untouched(
    tmp_path: Path,
) -> None:
    # e.g. a v1.0.0 database later opened by a from-source build, whose
    # create_all added the post-v1.0.0 tables without migrating anything.
    db_path = tmp_path / "budget.db"
    _make_v1_standalone_db(db_path)
    _execute(db_path, "CREATE TABLE bill_versions (id INTEGER PRIMARY KEY)")
    before = db_path.read_bytes()

    with pytest.raises(UnrecognizedDatabaseError, match="no migration history"):
        migrate_database(db_path, ALEMBIC_DIR, now=lambda: FIXED_NOW)

    assert db_path.read_bytes() == before
    assert _backups(db_path) == []


def test_database_from_a_newer_release_is_refused_untouched(tmp_path: Path) -> None:
    db_path = tmp_path / "budget.db"
    migrate_database(db_path, ALEMBIC_DIR, now=lambda: FIXED_NOW)
    _execute(db_path, "UPDATE alembic_version SET version_num = 'ffffffffffff'")
    before = db_path.read_bytes()

    with pytest.raises(UnrecognizedDatabaseError, match="newer release"):
        migrate_database(db_path, ALEMBIC_DIR, now=lambda: FIXED_NOW)

    assert db_path.read_bytes() == before
    assert _backups(db_path) == []


def test_existing_backup_is_never_overwritten(tmp_path: Path) -> None:
    db_path = tmp_path / "budget.db"
    _make_v1_standalone_db(db_path)
    clash = tmp_path / "budget.backup-20261004-113000.db"
    clash.write_bytes(b"earlier backup")

    with pytest.raises(FileExistsError):
        migrate_database(db_path, ALEMBIC_DIR, now=lambda: FIXED_NOW)

    assert clash.read_bytes() == b"earlier backup"
    assert "alembic_version" not in _tables(db_path)


def test_missing_migration_scripts_fail_loudly(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="env.py"):
        migrate_database(tmp_path / "budget.db", tmp_path / "nowhere")
