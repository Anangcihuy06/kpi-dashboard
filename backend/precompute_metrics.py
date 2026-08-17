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
from sqlalchemy import and_

import models
from feature_analyzer import calculate_feature_weight

logger = logging.getLogger("precompute_metrics")

COMPLETED_STATUSES = {
    "done", "resolved", "ready to release", "ready for uat",
    "uat (user)", "ready for qa", "in qa",
}


def _resolve_dt(ji):
    """Mirror the request-path date fallback logic exactly."""
    r_dt_naive = None
    if ji.resolved_date:
        r_dt = ji.resolved_date
        r_dt_naive = r_dt.replace(tzinfo=None) if hasattr(r_dt, "replace") else r_dt
    elif ji.raw_data and "fields" in (ji.raw_data or {}):
        fields = ji.raw_data["fields"]
        r_date_str = fields.get("resolutiondate") or fields.get("updated") or fields.get("created")
        if r_date_str:
            try:
                clean_date = r_date_str.split(".")[0]
                if "T" in clean_date:
                    r_dt_naive = datetime.strptime(clean_date, "%Y-%m-%dT%H:%M:%S")
                else:
                    r_dt = datetime.fromisoformat(clean_date.replace("Z", "+00:00"))
                    r_dt_naive = r_dt.replace(tzinfo=None)
            except Exception:
                r_dt_naive = None
    if not r_dt_naive and (ji.updated_date or ji.created_date):
        r_dt = ji.updated_date or ji.created_date
        r_dt_naive = r_dt.replace(tzinfo=None) if hasattr(r_dt, "replace") else r_dt
    return r_dt_naive


def _issue_complexity(ji):
    """Use the persisted complexity_score, falling back to the rules scorer."""
    if ji.complexity_score is not None:
        return float(ji.complexity_score)
    return float(calculate_feature_weight(ji.raw_data or {}))


def compute_user_year_metrics(db: Session, user, year: int) -> dict:
    """Aggregate one user's yearly delivery metrics. Idempotent upsert."""
    from_date = datetime(year, 1, 1)
    to_date = datetime(year, 12, 31, 23, 59, 59)

    raw_sp = 0.0
    complexity_sp = 0.0
    issues_completed = 0

    jira_ident = db.query(models.EmployeeIdentity).filter(
        and_(
            models.EmployeeIdentity.user_id == user.id,
            models.EmployeeIdentity.source == "jira",
        )
    ).first()

    if jira_ident and jira_ident.external_user_id:
        raw_issues = db.query(models.RawJiraIssue).filter(
            models.RawJiraIssue.assignee_account_id == jira_ident.external_user_id
        ).all()
        for ji in raw_issues:
            r_dt_naive = _resolve_dt(ji)
            if not (r_dt_naive and from_date <= r_dt_naive <= to_date):
                continue
            status_lower = (ji.status or "").lower()
            if status_lower not in COMPLETED_STATUSES:
                continue
            issues_completed += 1
            raw_sp += float(ji.story_points or 0.0)
            complexity_sp += _issue_complexity(ji)

    from founder_engine import get_founder_credits_for_user
    founder_credit = float(get_founder_credits_for_user(user.id, target_year=year) or 0.0)

    row = db.query(models.UserYearlyMetrics).filter(
        and_(
            models.UserYearlyMetrics.user_id == user.id,
            models.UserYearlyMetrics.year == year,
            models.UserYearlyMetrics.period == "YEARLY",
        )
    ).first()
    if row:
        row.raw_sp = raw_sp
        row.complexity_sp = complexity_sp
        row.issues_completed = issues_completed
        row.founder_credit = founder_credit
    else:
        row = models.UserYearlyMetrics(
            user_id=user.id,
            year=year,
            period="YEARLY",
            raw_sp=raw_sp,
            complexity_sp=complexity_sp,
            issues_completed=issues_completed,
            founder_credit=founder_credit,
        )
        db.add(row)

    return {
        "raw_sp": raw_sp,
        "complexity_sp": complexity_sp,
        "issues_completed": issues_completed,
        "founder_credit": founder_credit,
    }


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


def compute_all_year_metrics(db: Session, year: int, users=None, commit: bool = True) -> dict:
    """Compute UserYearlyMetrics for all active users + CompanyMaxima.

    Maxima are persisted at two scopes:
      - company-wide (group_id = NULL): benchmark across all active users
      - per group (group_id = user.group_id): benchmark scoped to each group's
        indicator matrix, so a group's relative score is compared to its peers.
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
        try:
            m = compute_user_year_metrics(db, u, year)
            per_user[u.id] = {"user": u, "metrics": m, "group_id": u.group_id, "division_id": u.division_id}
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
