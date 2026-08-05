from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def upsert_or_update[T](
    db: Session,
    lookup: Callable[[], T | None],
    build: Callable[[], T],
    apply_update: Callable[[T], None],
) -> T:
    """Find-then-write with a unique-constraint race handled as an update.

    A plain query-then-insert is racy: two requests for the same key can
    both see no row and both attempt an insert, and the loser hits an
    unhandled `IntegrityError` (BI-19). If the initial lookup finds nothing,
    the insert is attempted; on conflict, the session's transaction is
    rolled back (SQLite SAVEPOINTs aren't usable here without extra
    connection-level event wiring this app doesn't have — the pysqlite
    driver's own implicit transaction handling fights SQLAlchemy's SAVEPOINT
    support and leaves the session in a broken state) and the row the winner
    just inserted is updated instead.

    Because the rollback discards the caller's *whole* transaction, callers
    that write more than one row per request (e.g. `apply_rebalance_moves`)
    must commit after each call to this helper rather than batching a single
    commit at the end, or an unrelated earlier write in the same request
    would be lost alongside the losing insert.
    """
    row = lookup()
    if row is not None:
        apply_update(row)
        return row

    row = build()
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        row = lookup()
        if row is None:
            raise
        apply_update(row)
    return row
