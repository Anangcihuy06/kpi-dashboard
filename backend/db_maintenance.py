"""
DB maintenance: unique constraints + hot-path indexes, idempotent and
dialect-agnostic (SQLite + Postgres).

This is the single source of truth called from both:
  * ``main.py``  lifespan()  -> every normal startup
  * ``fix_production_db.py`` -> every deployment

Because SQLAlchemy ``create_all()`` never alters existing tables, model-level
UniqueConstraints only protect fresh installs. Existing production DBs get the
same guarantees here: we deduplicate leftover rows first, then create a UNIQUE
INDEX. Extra (non-unique) performance indexes are created next, gated behind
``AUTO_INDEX`` (default 1).
"""

import logging
import os

from sqlalchemy import text

logger = logging.getLogger("db_maintenance")

AUTO_INDEX = os.getenv("AUTO_INDEX", "1").lower() in ("1", "true", "yes")

# (index_name, table, columns) — unique, after dedup
UNIQUE_INDEXES = [
    ("ux_kpi_daily_user_date", "kpi_employee_daily", ["user_id", "date"]),
    ("ux_sync_state_source_entity", "sync_state", ["source", "entity"]),
    ("ux_project_source_external", "projects", ["source", "external_project_id"]),
]

# (index_name, table, columns) — plain query-path acceleration
EXTRA_INDEXES = [
    ("ix_activity_project_id", "activities", ["project_id"]),
    ("ix_activity_sprint_id", "activities", ["sprint_id"]),
    ("ix_attendance_sprint_id", "attendance_records", ["sprint_id"]),
    ("ix_sync_job_status", "sync_jobs", ["status"]),
    ("ix_sync_job_created", "sync_jobs", ["created_at"]),
    ("ix_sync_log_created", "sync_logs", ["created_at"]),
]


def _table_exists(inspector, table: str) -> bool:
    try:
        return table in inspector.get_table_names()
    except Exception:  # noqa: BLE001
        return False


def deduplicate_and_constrain(
    conn,
    table: str,
    index_name: str,
    group_cols,
    keep_col: str,
    keep_first: bool,
    only_non_null: str = None,
    prefer_referenced_by: list = None,
) -> list[str]:
    """Dedupe leftover duplicate rows for one table, then create a unique index.

    ``prefer_referenced_by`` is a list of (child_table, child_fk_column) pairs.
    When duplicates exist, a keeper that is already referenced by a child row is
    preferred so existing foreign keys stay valid.

    Returns a list of human-readable messages for logging.
    """
    msgs = []

    if only_non_null:
        where = f" AND {only_non_null} IS NOT NULL"
    else:
        where = ""
    groups = conn.execute(
        text(
            f"SELECT {', '.join(group_cols)} FROM {table} "
            f"WHERE 1=1{where} GROUP BY {', '.join(group_cols)} HAVING COUNT(*) > 1"
        )
    ).fetchall()

    removed = 0
    order_sql = f"{keep_col} ASC" if keep_first else f"{keep_col} DESC"
    for group in groups:
        params = {f"g{i}": g for i, g in enumerate(group)}
        where_grp = " AND ".join(
            f"{c} = :g{i}" for i, c in enumerate(group_cols)
        )
        if only_non_null:
            where_grp += f" AND {only_non_null} IS NOT NULL"

        row_ids = [
            r[0] for r in conn.execute(
                text(f"SELECT id FROM {table} WHERE {where_grp}"), params
            ).fetchall()
        ]

        # 1. Prefer a keeper that is already referenced by a child table.
        keep = None
        if prefer_referenced_by and len(row_ids) > 1:
            for ref_table, ref_col in prefer_referenced_by:
                try:
                    refs = {
                        r[0] for r in conn.execute(
                            text(
                                f"SELECT DISTINCT {ref_col} FROM {ref_table} "
                                f"WHERE {ref_col} IN ({', '.join(':k' + str(i) for i in range(len(row_ids)))})"
                            ),
                            {f"k{i}": rid for i, rid in enumerate(row_ids)},
                        ).fetchall()
                    }
                except Exception:  # noqa: BLE001 - child table missing/malformed
                    refs = set()
                referenced = refs & set(row_ids)
                if referenced:
                    keep = referenced.pop()
                    break

        # 2. Fallback: keep per keep_first direction on keep_col (nulls last),
        #    then lexicographically by id for stability.
        if keep is None:
            direction = "ASC" if keep_first else "DESC"
            keep = conn.execute(
                text(
                    f"SELECT id FROM {table} WHERE {where_grp} "
                    f"ORDER BY {keep_col} IS NULL ASC, {keep_col} {direction}, id ASC LIMIT 1"
                ),
                params,
            ).scalar()
        if keep is None:
            continue
        params["keep"] = keep
        res = conn.execute(
            text(f"DELETE FROM {table} WHERE {where_grp} AND id != :keep"),
            params,
        )
        removed += res.rowcount or 0

    if removed:
        msgs.append(f"  - {table}: removed {removed} duplicate rows")

    cols_sql = ", ".join(group_cols)
    conn.execute(
        text(
            f"CREATE UNIQUE INDEX IF NOT EXISTS {index_name} "
            f"ON {table} ({cols_sql})"
        )
    )
    msgs.append(f"  - ensured unique index {index_name} ON {table} ({cols_sql})")
    return msgs


def run_db_maintenance(engine) -> list[str]:
    """Entry point. Safe to call on every startup/deploy. Returns log lines."""
    msgs = ["DB maintenance:"]
    if not AUTO_INDEX:
        msgs.append("  - AUTO_INDEX disabled; skipping unique + perf indexes")
        return msgs

    from sqlalchemy import inspect as sa_inspect

    inspector = sa_inspect(engine)
    try:
        with engine.begin() as conn:
            # Verify indexes don't already exist with the same name (both
            # backends tolerate IF NOT EXISTS, but listing is cheap & clear).
            existing = set()
            for tab in inspector.get_table_names():
                for idx in inspector.get_indexes(tab):
                    existing.add(idx.get("name"))

            # 1. kpi_employee_daily (user_id, date) — keep newest calculation
            if _table_exists(inspector, "kpi_employee_daily") and "ux_kpi_daily_user_date" not in existing:
                msgs.extend(
                    deduplicate_and_constrain(
                        conn, "kpi_employee_daily", "ux_kpi_daily_user_date",
                        ["user_id", "date"], "calculated_at", keep_first=False,
                    )
                )

            # 2. sync_state (source, entity) — keep newest update
            if _table_exists(inspector, "sync_state") and "ux_sync_state_source_entity" not in existing:
                msgs.extend(
                    deduplicate_and_constrain(
                        conn, "sync_state", "ux_sync_state_source_entity",
                        ["source", "entity"], "updated_at", keep_first=False,
                    )
                )

            # 3. projects (source, external_project_id) — keep a copy that is
            #    referenced by child rows (issues/activities/kpi_employee_daily),
            #    otherwise the oldest by created_at, so existing FKs stay valid
            if _table_exists(inspector, "projects") and "ux_project_source_external" not in existing:
                msgs.extend(
                    deduplicate_and_constrain(
                        conn, "projects", "ux_project_source_external",
                        ["source", "external_project_id"], "created_at", keep_first=True,
                        only_non_null="external_project_id",
                        prefer_referenced_by=[
                            ("activities", "project_id"),
                            ("issues", "project_id"),
                            ("kpi_employee_daily", "project_id"),
                        ],
                    )
                )

            # 4. Extra performance indexes
            for name, table, cols in EXTRA_INDEXES:
                if not _table_exists(inspector, table):
                    continue
                if name in existing:
                    continue
                conn.execute(
                    text(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({', '.join(cols)})")
                )
                msgs.append(f"  - ensured index {name} ON {table} ({', '.join(cols)})")
    except Exception as e:  # noqa: BLE001
        logger.error(f"DB maintenance failed: {e}")
        msgs.append(f"  - ERROR: {e}")
    return msgs


def ensure_constraints_and_indexes(engine) -> None:
    """Thin wrapper that logs and swallows failures (never blocks startup)."""
    try:
        lines = run_db_maintenance(engine)
        for line in lines:
            logger.info(line)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"ensure_constraints_and_indexes skipped: {e}")