"""
Precompute service: computes per-user yearly delivery aggregates and the
company-wide 5-pillar maxima once at sync time, persisting them so request
paths are cheap DB reads (never rescan/re-analyze raw Jira issues).

Data written:
  - UserYearlyMetrics : per user + year {raw_sp, complexity_sp, issues_completed, founder_credit}
  - CompanyMaxima     : per year {max_raw_sp, max_complexity_sp, max_issues_cnt, max_founder_sp}
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_, func

import models

logger = logging.getLogger("precompute_metrics")

COMPLETED_STATUSES = {
    "done", "resolved", "ready to release", "ready for uat",
    "uat (user)", "ready for qa", "in qa",
}


class PrecomputeCancelled(Exception):
    """Raised when a running KPI calc job is cancelled during the precompute phase."""


def compute_user_year_metrics(db: Session, user, year: int, last_processed_date=None):
    """Aggregate one user's yearly delivery metrics via a single SQL query.

    Replaces the old row-by-row Python loop (which loaded every RawJiraIssue
    including its raw_data JSON and ran feature analysis per issue). The whole
    year now resolves to one GROUP-aggregate: minutes -> seconds.

    When last_processed_date is given, only rows resolved after it are summed,
    so stored totals can be incremented instead of recomputed from scratch.
    Returns (metrics_dict, max_processed_datetime).
    """
    from_date = datetime(year, 1, 1)
    to_date = datetime(year, 12, 31, 23, 59, 59)

    raw_sp = 0.0
    complexity_sp = 0.0
    issues_completed = 0
    max_date = last_processed_date

    jira_ident = db.query(models.EmployeeIdentity).filter(
        and_(
            models.EmployeeIdentity.user_id == user.id,
            models.EmployeeIdentity.source == "jira",
        )
    ).first()

    if jira_ident and jira_ident.external_user_id:
        q = db.query(
            func.coalesce(func.sum(models.RawJiraIssue.story_points), 0),
            func.coalesce(func.sum(func.coalesce(models.RawJiraIssue.complexity_score, 0.0)), 0),
            func.count(),
            func.max(models.RawJiraIssue.resolved_date),
        ).filter(
            models.RawJiraIssue.assignee_account_id == jira_ident.external_user_id,
            models.RawJiraIssue.resolved_date >= from_date,
            models.RawJiraIssue.resolved_date <= to_date,
            func.lower(models.RawJiraIssue.status).in_([s for s in COMPLETED_STATUSES]),
        )
        if last_processed_date is not None:
            q = q.filter(models.RawJiraIssue.resolved_date > last_processed_date)
        sp_sum, cx_sum, cnt, mdate = q.one()
        raw_sp = float(sp_sum or 0.0)
        complexity_sp = float(cx_sum or 0.0)
        issues_completed = int(cnt or 0)
        if mdate is not None and (max_date is None or mdate > max_date):
            max_date = mdate

    from founder_engine import get_founder_credits_for_user
    founder_credit = float(get_founder_credits_for_user(user.id, target_year=year) or 0.0)

    return {
        "raw_sp": raw_sp,
        "complexity_sp": complexity_sp,
        "issues_completed": issues_completed,
        "founder_credit": founder_credit,
    }, max_date


def _upsert_maxima(db, year, group_id, division_id, maxima, commit=False):
    cm = db.query(models.CompanyMaxima).filter(
        and_(
            models.CompanyMaxima.year == year,
            models.CompanyMaxima.period == "YEARLY",
            models.CompanyMaxima.group_id.is_(group_id) if group_id is None
            else models.CompanyMaxima.group_id == group_id,
        )
    ).first()
    if cm:
        cm.max_raw_sp = maxima["max_raw_sp"]
        cm.max_complexity_sp = maxima["max_complexity_sp"]
        cm.max_issues_cnt = maxima["max_issues_cnt"]
        cm.max_founder_sp = maxima["max_founder_sp"]
        cm.division_id = division_id
    else:
        cm = models.CompanyMaxima(
            year=year,
            period="YEARLY",
            group_id=group_id,
            division_id=division_id,
            max_raw_sp=maxima["max_raw_sp"],
            max_complexity_sp=maxima["max_complexity_sp"],
            max_issues_cnt=maxima["max_issues_cnt"],
            max_founder_sp=maxima["max_founder_sp"],
        )
        db.add(cm)
    if commit:
        db.commit()


def compute_all_year_metrics(db: Session, year: int, users=None, commit: bool = True, is_cancelled=None, force: bool = False) -> dict:
    """Compute UserYearlyMetrics for all active users + CompanyMaxima.

    Uses SQL aggregation (seconds instead of minutes). Runs incrementally when a
    UserYearlyMetrics.last_processed_date marker exists: only rows resolved after
    the marker are summed and added to the stored totals. A NULL marker forces a
    full recompute (replacing stored totals). Pass force=True to ignore the
    marker (used after a rescore, since backfilled values affect old dates too).

    is_cancelled: optional callable -> bool, polled between users so a
    background job that was cancelled during the precompute phase stops early
    (raises PrecomputeCancelled) instead of resurrecting itself as COMPLETED.
    """
    if users is None:
        users = db.query(models.User).filter(models.User.is_active == True).all()

    def _empty_maxima():
        return {
            "max_raw_sp": 1.0,
            "max_complexity_sp": 1.0,
            "max_issues_cnt": 1,
            "max_founder_sp": 1.0,
        }

    per_user = {}
    for u in users:
        if is_cancelled and is_cancelled():
            logger.warning(f"Precompute cancelled for year {year}")
            db.rollback()
            raise PrecomputeCancelled(f"precompute cancelled for year {year}")
        try:
            existing = db.query(models.UserYearlyMetrics).filter(
                and_(
                    models.UserYearlyMetrics.user_id == u.id,
                    models.UserYearlyMetrics.year == year,
                    models.UserYearlyMetrics.period == "YEARLY",
                )
            ).first()
            last = (None if force else existing.last_processed_date) if existing else None
            m, max_date = compute_user_year_metrics(db, u, year, last_processed_date=last)
            if existing:
                if last is None:
                    # Full recompute: replace stored totals.
                    existing.raw_sp = m["raw_sp"]
                    existing.complexity_sp = m["complexity_sp"]
                    existing.issues_completed = m["issues_completed"]
                else:
                    # Incremental: add only the delta since the marker.
                    existing.raw_sp = float(existing.raw_sp or 0.0) + m["raw_sp"]
                    existing.complexity_sp = float(existing.complexity_sp or 0.0) + m["complexity_sp"]
                    existing.issues_completed = int(existing.issues_completed or 0) + m["issues_completed"]
                existing.founder_credit = m["founder_credit"]
                if max_date is not None:
                    existing.last_processed_date = max_date
            else:
                existing = models.UserYearlyMetrics(
                    user_id=u.id,
                    year=year,
                    period="YEARLY",
                    raw_sp=m["raw_sp"],
                    complexity_sp=m["complexity_sp"],
                    issues_completed=m["issues_completed"],
                    founder_credit=m["founder_credit"],
                    last_processed_date=max_date,
                )
                db.add(existing)
            per_user[u.id] = {
                "user": u,
                "metrics": {
                    "raw_sp": float(existing.raw_sp or 0.0),
                    "complexity_sp": float(existing.complexity_sp or 0.0),
                    "issues_completed": int(existing.issues_completed or 0),
                    "founder_credit": float(existing.founder_credit or 0.0),
                },
                "group_id": u.group_id,
                "division_id": u.division_id,
            }
        except Exception as e:  # noqa: BLE001
            logger.error(f"compute_user_year_metrics failed for {u.id} year {year}: {e}")
            db.rollback()

    # Company-wide maxima across all active users
    global_maxima = _empty_maxima()
    for data in per_user.values():
        m = data["metrics"]
        global_maxima["max_raw_sp"] = max(global_maxima["max_raw_sp"], m["raw_sp"] or 1.0)
        global_maxima["max_complexity_sp"] = max(global_maxima["max_complexity_sp"], m["complexity_sp"] or 1.0)
        global_maxima["max_issues_cnt"] = max(global_maxima["max_issues_cnt"], m["issues_completed"] or 1)
        global_maxima["max_founder_sp"] = max(global_maxima["max_founder_sp"], m["founder_credit"] or 1.0)

    _upsert_maxima(db, year, None, None, global_maxima)

    # Per-group maxima (each group's own indicator-matrix benchmark)
    groups = {}
    for data in per_user.values():
        gid = data["group_id"]
        if not gid:
            continue
        groups.setdefault(gid, _empty_maxima())
        m = data["metrics"]
        g = groups[gid]
        g["max_raw_sp"] = max(g["max_raw_sp"], m["raw_sp"] or 1.0)
        g["max_complexity_sp"] = max(g["max_complexity_sp"], m["complexity_sp"] or 1.0)
        g["max_issues_cnt"] = max(g["max_issues_cnt"], m["issues_completed"] or 1)
        g["max_founder_sp"] = max(g["max_founder_sp"], m["founder_credit"] or 1.0)

    for gid, maxima in groups.items():
        division_id = next((d["division_id"] for d in per_user.values() if d["group_id"] == gid), None)
        _upsert_maxima(db, year, gid, division_id, maxima)

    if commit:
        db.commit()

    logger.info(
        f"Precomputed year {year}: global raw_sp={global_maxima['max_raw_sp']}, "
        f"complexity={global_maxima['max_complexity_sp']}, issues={global_maxima['max_issues_cnt']}, "
        f"founder={global_maxima['max_founder_sp']}, groups={len(groups)}"
    )
    return global_maxima


def get_company_maxima(db: Session, year: int, group_id: Optional[str] = None) -> dict:
    """Fast DB read of persisted maxima at the requested scope (no scanning).

    group_id=None reads the company-wide benchmark; a group_id reads that
    group's benchmark (its own indicator-matrix peak).
    """
    q = db.query(models.CompanyMaxima).filter(
        and_(
            models.CompanyMaxima.year == year,
            models.CompanyMaxima.period == "YEARLY",
        )
    )
    q = q.filter(models.CompanyMaxima.group_id == group_id) if group_id else q.filter(models.CompanyMaxima.group_id.is_(None))
    cm = q.first()
    if not cm:
        return None
    return {
        "max_raw_sp": float(cm.max_raw_sp),
        "max_complexity_sp": float(cm.max_complexity_sp),
        "max_issues_cnt": int(cm.max_issues_cnt),
        "max_founder_sp": float(cm.max_founder_sp),
    }


def get_user_year_metrics(db: Session, user_id: str, year: int) -> dict:
    """Fast DB read of one user's yearly aggregate (no scanning)."""
    row = db.query(models.UserYearlyMetrics).filter(
        and_(
            models.UserYearlyMetrics.user_id == user_id,
            models.UserYearlyMetrics.year == year,
            models.UserYearlyMetrics.period == "YEARLY",
        )
    ).first()
    if not row:
        return None
    return {
        "raw_sp": float(row.raw_sp),
        "complexity_sp": float(row.complexity_sp),
        "issues_completed": int(row.issues_completed),
        "founder_credit": float(row.founder_credit),
    }
