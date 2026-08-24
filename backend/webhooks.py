"""
Trigger-driven worker entry points for Jira / GitLab.

The heavy sync is never run on the request-scoped DB session (that session can
be closed/poisoned while the background task is still running). Instead every
webhook:
  1. creates a SyncJob row (returned immediately so the caller can poll),
  2. queues a background task that opens its own SessionLocal().

Bursts of webhooks for the same user are debounced (WEBHOOK_DEBOUNCE_MINUTES)
so we do not hammer the upstream Jira/GitLab APIs.
"""

import hashlib
import hmac
import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
import models

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])
logger = logging.getLogger("Webhooks")

WEBHOOK_DEBOUNCE_SECONDS = int(os.getenv("WEBHOOK_DEBOUNCE_MINUTES", "5")) * 60

_recent_webhooks = {}
_recent_lock = threading.Lock()


def _is_debounced(user_id: str) -> bool:
    """True when a sync for this user was already queued in the last window."""
    now = time.time()
    with _recent_lock:
        last = _recent_webhooks.get(user_id)
        if last is not None and (now - last) < WEBHOOK_DEBOUNCE_SECONDS:
            # Refresh the timestamp so a burst keeps suppressing duplicates.
            _recent_webhooks[user_id] = now
            return True
        _recent_webhooks[user_id] = now
        return False


async def _read_and_verify(request: Request, secret_env: str):
    """Read the raw body once and (optionally) verify the HMAC signature.

    Returns (payload_dict, ok). Verification is skipped when the secret env
    var is empty (local/dev convenience).
    """
    body = await request.body()
    secret = os.getenv(secret_env, "")
    if secret:
        provided = (request.headers.get("X-Hub-Signature") or "").split("=", 1)[-1]
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha1).hexdigest()
        if not provided or not hmac.compare_digest(provided, expected):
            logger.warning(f"Webhook signature check failed ({secret_env})")
            return {}, False
    try:
        return json.loads(body or b"{}"), True
    except Exception:  # noqa: BLE001
        return {}, True


def _queue_sync(db: Session, user_id: str, background_tasks: BackgroundTasks):
    """Create a SyncJob row + queue a task on its own session. Returns summary."""
    if _is_debounced(user_id):
        return {"user_id": user_id, "skipped": True, "reason": "debounced"}

    from sync_engine import create_sync_job, update_job_progress, mark_job_completed, mark_job_failed

    job_id = create_sync_job(db, user_id, "WEBHOOK_SYNC")
    logger.info(f"Webhook queuing WEBHOOK_SYNC {job_id} for user {user_id}")

    def run(jid: str):
        from database import SessionLocal
        from comprehensive_sync import sync_user_comprehensive

        s = SessionLocal()
        try:
            update_job_progress(s, jid, 10, "RUNNING")
            user = s.query(models.User).filter(models.User.id == user_id).first()
            settings = s.query(models.IntegrationSetting).first()
            if not user or not settings:
                mark_job_failed(s, jid, "user or settings not found")
                return
            start_date = datetime.now() - timedelta(days=2)
            end_date = datetime.now() + timedelta(days=1)
            result = sync_user_comprehensive(s, user, settings, start_date, end_date)
            mark_job_completed(s, jid, {"user": user_id, "user_name": user.full_name, "result": result})
        except Exception as e:  # noqa: BLE001
            logger.error(f"Webhook sync failed for user {user_id}: {e}")
            try:
                s.rollback()
            except Exception:  # noqa: BLE001
                pass
            mark_job_failed(s, jid, str(e))
        finally:
            s.close()

    background_tasks.add_task(run, job_id)
    return {"user_id": user_id, "job_id": job_id, "skipped": False}


def _find_jira_user(db: Session, account_id: str = None, email: str = None):
    """Resolve a Jira accountId/email to a local User (identity-first)."""
    if account_id:
        ident = (
            db.query(models.EmployeeIdentity)
            .filter(
                models.EmployeeIdentity.source == "jira",
                models.EmployeeIdentity.external_user_id == account_id,
            )
            .first()
        )
        if ident:
            return db.query(models.User).filter(models.User.id == ident.user_id).first()
    if email:
        return db.query(models.User).filter(models.User.email == email).first()
    return None


@router.post("/gitlab")
async def gitlab_webhook(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Handle GitLab webhooks for pushes and merge requests."""
    payload, ok = await _read_and_verify(request, "WEBHOOK_SECRET_GITLAB")
    if not ok:
        return JSONResponse({"status": "error", "message": "invalid signature"}, status_code=403)

    event_type = request.headers.get("X-Gitlab-Event", "")
    logger.info(f"Received GitLab Webhook: {event_type}")

    queued = []
    seen_emails = set()
    if event_type == "Push Hook":
        for commit in payload.get("commits", []):
            email = (commit.get("author") or {}).get("email")
            if not email or email in seen_emails:
                continue
            seen_emails.add(email)
            user = db.query(models.User).filter(models.User.email == email).first()
            if user:
                queued.append(_queue_sync(db, user.id, background_tasks))
    elif event_type in ("Merge Request Hook", "Note Hook"):
        author = payload.get("user") or {}
        email = author.get("email")
        if email:
            user = db.query(models.User).filter(models.User.email == email).first()
            if user:
                queued.append(_queue_sync(db, user.id, background_tasks))

    return {"status": "success", "message": f"Queued {len(queued)} user sync(s)", "queued": queued}


@router.post("/jira")
async def jira_webhook(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Handle Jira webhooks for issue created / updated / worklog events."""
    payload, ok = await _read_and_verify(request, "WEBHOOK_SECRET_JIRA")
    if not ok:
        return JSONResponse({"status": "error", "message": "invalid signature"}, status_code=403)

    event_type = payload.get("webhookEvent", "")
    logger.info(f"Received Jira Webhook: {event_type}")

    issue = payload.get("issue", {}) or {}
    fields = issue.get("fields", {}) or {}
    queued = []
    for candidate in (fields.get("assignee"), fields.get("reporter")):
        if not candidate:
            continue
        user = _find_jira_user(
            db,
            account_id=candidate.get("accountId"),
            email=candidate.get("emailAddress"),
        )
        if user:
            queued.append(_queue_sync(db, user.id, background_tasks))
            break  # one sync per event, assignee takes priority

    return {"status": "success", "message": f"Queued {len(queued)} user sync(s)", "queued": queued}