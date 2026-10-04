"""Bring a standalone SQLite database up to the current schema (BI-68).

Docker runs ``alembic upgrade head`` before the server starts. The standalone
build used ``Base.metadata.create_all`` instead, which creates missing tables
but never alters existing ones, so its databases carry no ``alembic_version``
and would never pick up a later migration.

``migrate_database`` sorts a database into one of four states:

* **fresh** (no tables): ``upgrade head``, exactly what Docker does.
* **versioned** (has ``alembic_version``): ``upgrade head`` if behind.
* **v1.0.0 standalone** (unversioned, v1.0.0's table set): stamp at
  ``LEGACY_V1_REVISION`` and upgrade. A v1.0.0 ``create_all`` database was
  verified to match the migrations at that revision.
* anything else unversioned: refused. Stamping a schema we can't identify
  would silently skip or repeat migrations.

Any database that already holds data is copied to a timestamped backup before
the first write.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.util.exc import CommandError
from sqlalchemy import Engine, create_engine, inspect

from alembic import command

# Head of the migration chain shipped in the v1.0.0 release.
LEGACY_V1_REVISION = "c3d4e5f6a7b8"
VERSION_TABLE = "alembic_version"
# Present in every v1.0.0 database; dropped by a later migration.
_V1_ONLY_TABLE = "pay_periods"
# Created by migrations after v1.0.0; a v1.0.0 database has neither.
_POST_V1_TABLES = frozenset({"bill_versions", "pay_period_actuals"})


class MigrationAction(StrEnum):
    created = "created"
    up_to_date = "up_to_date"
    upgraded = "upgraded"
    legacy_upgraded = "legacy_upgraded"


@dataclass(frozen=True)
class MigrationResult:
    action: MigrationAction
    backup_path: Path | None = None


class UnrecognizedDatabaseError(RuntimeError):
    """The database's schema can't be matched to a known migration state."""


def migrate_database(
    db_path: Path,
    script_location: Path,
    *,
    now: Callable[[], datetime] = datetime.now,
) -> MigrationResult:
    """Upgrade the SQLite database at *db_path* to the latest migration."""
    config = _alembic_config(script_location)
    script = ScriptDirectory.from_config(config)
    head = script.get_current_head()
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    try:
        tables = set(inspect(engine).get_table_names())
        if not tables:
            _upgrade(engine, config)
            return MigrationResult(MigrationAction.created)

        if VERSION_TABLE in tables:
            current = _current_revision(engine)
            if current == head:
                return MigrationResult(MigrationAction.up_to_date)
            if current is not None and not _is_known_revision(script, current):
                raise UnrecognizedDatabaseError(
                    f"{db_path} is at migration {current}, which this version "
                    "of Budget-inator doesn't know. It was probably written by "
                    "a newer release; run that release instead."
                )
            backup = _back_up(engine, db_path, now)
            _upgrade(engine, config)
            return MigrationResult(MigrationAction.upgraded, backup)

        if _V1_ONLY_TABLE in tables and not tables & _POST_V1_TABLES:
            backup = _back_up(engine, db_path, now)
            with engine.begin() as connection:
                config.attributes["connection"] = connection
                command.stamp(config, LEGACY_V1_REVISION)
            _upgrade(engine, config)
            return MigrationResult(MigrationAction.legacy_upgraded, backup)

        raise UnrecognizedDatabaseError(
            f"{db_path} has no migration history and doesn't match the "
            f"v1.0.0 layout (tables: {', '.join(sorted(tables))}). It was left "
            "unchanged. Move it aside to start fresh, or report this so it "
            "can be upgraded safely."
        )
    finally:
        engine.dispose()


def _alembic_config(script_location: Path) -> Config:
    if not (script_location / "env.py").is_file():
        raise FileNotFoundError(f"no Alembic env.py under {script_location}")
    config = Config()
    config.set_main_option("script_location", str(script_location))
    return config


def _upgrade(engine: Engine, config: Config) -> None:
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


def _current_revision(engine: Engine) -> str | None:
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def _is_known_revision(script: ScriptDirectory, revision: str) -> bool:
    try:
        return script.get_revision(revision) is not None
    except CommandError:  # what alembic raises for an id it has no script for
        return False


def _back_up(engine: Engine, db_path: Path, now: Callable[[], datetime]) -> Path:
    # Close pooled connections so the copy sees a quiescent file.
    engine.dispose()
    stamp = now().strftime("%Y%m%d-%H%M%S")
    backup = db_path.with_name(f"{db_path.stem}.backup-{stamp}{db_path.suffix}")
    if backup.exists():
        raise FileExistsError(f"backup {backup} already exists; not overwriting")
    shutil.copy2(db_path, backup)
    return backup
