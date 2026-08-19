"""
DB-based advisory lock for cross-instance mutual exclusion.

Railway can run more than one uvicorn worker/instance and the scheduler may stay
in-process; a threading.Lock is invisible to other processes. This module
provides a lock row inside the database (identical mechanics on SQLite and
Postgres) so two instances can never run the same heavy job (KPI calculation,
full sync, rescore) at the same time.

Mechanics
---------
- The lock state is a single row in ``app_locks`` keyed by ``lock_name``.
- Acquire is an atomic ``INSERT ... ON CONFLICT DO NOTHING``. On conflict the
  row is treated as held UNLESS it is stale (heartbeat older than the TTL); a
  stale lock is "stolen" with a guarded UPDATE that only succeeds if it matched
  exactly one row with the old heartbeat.
- ``keepalive()`` refreshes the heartbeat so long-running jobs do not appear
  stale. ``release()`` deletes the row.

Usage
-----
    from database import engine
    from locks import AppLock, try_acquire, release

    if try_acquire(engine, "KPI_CALC", owner=os.getpid()):
        try:
            ... heavy work, calling keepalive(engine, "KPI_CALC") as you go ...
        finally:
            release(engine, "KPI_CALC")

Or with the context manager:

    with AppLock(engine, "KPI_CALC").acquire() as ok:
        if ok:
            ...
"""

import logging
import os
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import text

logger = logging.getLogger("locks")

DEFAULT_TTL_SECONDS = int(os.getenv("CALC_LOCK_TTL_MINUTES", "360")) * 60

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS app_locks (
    lock_name    VARCHAR(150) PRIMARY KEY,
    owner        VARCHAR(100),
    acquired_at  VARCHAR(30),
    heartbeat_at VARCHAR(30)
)
"""


def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def _parse(iso_value) -> datetime | None:
    if not iso_value:
        return None
    try:
        return datetime.fromisoformat(str(iso_value))
    except Exception:  # noqa: BLE001
        return None


def ensure_app_locks_table(engine) -> None:
    """Idempotent table bootstrap. Safe to call on every startup."""
    try:
        with engine.begin() as conn:
            conn.execute(text(_CREATE_TABLE_SQL))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Could not ensure app_locks table: {e}")


def try_acquire(engine, lock_name: str, ttl_seconds: int = DEFAULT_TTL_SECONDS,
                owner: str = None) -> bool:
    """Try to acquire the named lock. Returns True on success."""
    if not lock_name:
        return False
    ensure_app_locks_table(engine)
    now = _now()
    owner = owner or f"{os.getpid()}"
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        res = conn.execute(
            text(
                "INSERT INTO app_locks (lock_name, owner, acquired_at, heartbeat_at) "
                "VALUES (:n, :o, :now, :now) "
                "ON CONFLICT (lock_name) DO NOTHING"
            ),
            {"n": lock_name, "o": owner, "now": now},
        )
        if res.rowcount == 1:
            logger.info(f"Acquired lock '{lock_name}' (owner={owner})")
            return True

        # Lock already exists. Steal only if its heartbeat is stale.
        row = conn.execute(
            text("SELECT heartbeat_at FROM app_locks WHERE lock_name = :n"),
            {"n": lock_name},
        ).fetchone()
        if row is None:
            # Lost row between insert-conflict and read: retry the insert.
            res = conn.execute(
                text(
                    "INSERT INTO app_locks (lock_name, owner, acquired_at, heartbeat_at) "
                    "VALUES (:n, :o, :now, :now) ON CONFLICT (lock_name) DO NOTHING"
                ),
                {"n": lock_name, "o": owner, "now": now},
            )
            return res.rowcount == 1

        last_hb = _parse(row[0])
        if last_hb is None or (datetime.utcnow() - last_hb).total_seconds() > ttl_seconds:
            old_hb = row[0]
            upd = conn.execute(
                text(
                    "UPDATE app_locks SET acquired_at = :now, heartbeat_at = :now, owner = :o "
                    "WHERE lock_name = :n AND heartbeat_at = :old_hb"
                ),
                {"now": now, "o": owner, "n": lock_name, "old_hb": old_hb},
            )
            if upd.rowcount == 1:
                logger.warning(f"Stole stale lock '{lock_name}' (owner={owner})")
                return True
        return False


def keepalive(engine, lock_name: str) -> bool:
    """Refresh a held lock's heartbeat. Returns True on success."""
    ensure_app_locks_table(engine)
    now = _now()
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        res = conn.execute(
            text("UPDATE app_locks SET heartbeat_at = :now WHERE lock_name = :n"),
            {"now": now, "n": lock_name},
        )
        return res.rowcount == 1


def release(engine, lock_name: str) -> bool:
    """Release a held lock. Returns True if a row was actually removed."""
    ensure_app_locks_table(engine)
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        res = conn.execute(
            text("DELETE FROM app_locks WHERE lock_name = :n"),
            {"n": lock_name},
        )
        return res.rowcount == 1


class AppLock:
    """Small wrapper so callers use the lock without sprinkling raw SQL."""

    def __init__(self, engine, lock_name: str, owner: str = None,
                 ttl_seconds: int = None):
        self.engine = engine
        self.lock_name = lock_name
        self.owner = owner or f"{os.getpid()}"
        self.ttl_seconds = ttl_seconds or DEFAULT_TTL_SECONDS
        self.acquired = False

    def try_acquire(self) -> bool:
        self.acquired = try_acquire(
            self.engine, self.lock_name,
            ttl_seconds=self.ttl_seconds, owner=self.owner,
        )
        return self.acquired

    def keepalive(self) -> bool:
        if not self.acquired:
            return False
        return keepalive(self.engine, self.lock_name)

    def release(self) -> bool:
        if not self.acquired:
            return False
        self.acquired = False
        return release(self.engine, self.lock_name)

    @contextmanager
    def acquire(self):
        ok = self.try_acquire()
        try:
            yield ok
        finally:
            if ok:
                try:
                    self.keepalive()
                except Exception:  # noqa: BLE001
                    pass
                self.release()