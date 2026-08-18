import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
import models

def create_sync_job(db: Session, user_id: str, job_type: str) -> str:
    """Create a new sync job and return its ID"""
    job = models.SyncJob(
        user_id=user_id,
        job_type=job_type,
        status="PENDING",
        progress=0,
        started_at=datetime.now()
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job.id

def mark_stale_jobs_failed(db: Session, job_type: str = None, max_age_minutes: int = 60):
    """Mark jobs stuck in PENDING/RUNNING as FAILED.

    Railway (re)deploys kill in-process background tasks. A job left in
    PENDING/RUNNING with no progress updates for a long time means its worker
    was killed, so it will never complete. Clean these up before creating a
    new job so polling can't hang on zombie statuses.
    """
    cutoff = datetime.now() - timedelta(minutes=max_age_minutes)
    q = db.query(models.SyncJob).filter(
        models.SyncJob.status.in_(["PENDING", "RUNNING"])
    )
    if job_type:
        q = q.filter(models.SyncJob.job_type == job_type)
    stale = q.all()
    marked = 0
    for job in stale:
        ref_time = job.updated_at or job.started_at or job.created_at
        # A job that updates progress keeps touching updated_at, so it is NOT stale.
        if not ref_time or ref_time >= cutoff:
            continue
        job.status = "FAILED"
        job.error_message = "Job dibatalkan: worker dihentikan (redeploy/restart) sebelum selesai. Silakan jalankan ulang."
        job.completed_at = datetime.now()
        marked += 1
    if marked:
        db.commit()
    return marked

def update_job_progress(db: Session, job_id: str, progress: int, status: str = "RUNNING"):
    """Update job progress safely.

    Skips the write when the progress value did not change, so the high-frequency
    calls (per date during KPI calc) do not spam thousands of DB commits while
    still refreshing updated_at whenever the percentage actually moves.
    """
    job = db.query(models.SyncJob).filter(models.SyncJob.id == job_id).first()
    if not job:
        return
    if job.progress == progress and job.status == status:
        return
    job.progress = progress
    job.status = status
    db.commit()

def mark_job_completed(db: Session, job_id: str, result: dict = None):
    """Mark job as completed"""
    job = db.query(models.SyncJob).filter(models.SyncJob.id == job_id).first()
    if job:
        job.status = "COMPLETED"
        job.progress = 100
        job.result = result
        job.completed_at = datetime.now()
        db.commit()

def mark_job_failed(db: Session, job_id: str, error: str):
    """Mark job as failed"""
    job = db.query(models.SyncJob).filter(models.SyncJob.id == job_id).first()
    if job:
        job.status = "FAILED"
        job.error_message = error
        job.completed_at = datetime.now()
        db.commit()

def mark_single_stale_job_failed(db: Session, job: models.SyncJob):
    """Mark THIS job FAILED if it is stuck PENDING/RUNNING and too old.

    Railway redeploys kill in-process background tasks, leaving the job stuck
    RUNNING forever. The frontend polls a single job — so the poll itself must
    resolve the zombie state, otherwise the UI hangs on a spinner with a 200 OK
    response that never changes.

    Uses updated_at so a worker that refreshes progress (per user / per date) is
    never misclassified as stale, even when the whole run takes far longer than
    15 minutes.
    """
    if job.status not in ("PENDING", "RUNNING"):
        return job
    cutoff = datetime.now() - timedelta(minutes=60)
    ref_time = job.updated_at or job.started_at or job.created_at
    if ref_time and ref_time < cutoff:
        job.status = "FAILED"
        job.error_message = "Job dibatalkan: worker dihentikan (redeploy/restart) sebelum selesai. Silakan jalankan ulang."
        job.completed_at = datetime.now()
        db.commit()
    return job


def get_job_status(db: Session, job_id: str):
    """Get the status of a specific job"""
    job = db.query(models.SyncJob).filter(models.SyncJob.id == job_id).first()
    if not job:
        return None

    job = mark_single_stale_job_failed(db, job)
    return {
        "job_id": job.id,
        "status": job.status,
        "progress": job.progress,
        "result": job.result,
        "error": job.error_message,
        "started_at": job.started_at,
        "completed_at": job.completed_at
    }

def get_active_sync_status(db: Session):
    """Check if any sync job is currently running"""
    active_jobs = db.query(models.SyncJob).filter(models.SyncJob.status.in_(["PENDING", "RUNNING"])).all()
    is_syncing = len(active_jobs) > 0
    
    # Get last completed sync
    last_sync = db.query(models.SyncJob).filter(
        models.SyncJob.status == "COMPLETED"
    ).order_by(models.SyncJob.completed_at.desc()).first()
    
    return {
        "is_syncing": is_syncing,
        "active_jobs_count": len(active_jobs),
        "last_sync_time": last_sync.completed_at.isoformat() if last_sync and last_sync.completed_at else None,
        "last_sync_timestamp": int(last_sync.completed_at.timestamp()) if last_sync and last_sync.completed_at else None,
        "sync_interval_minutes": 60
    }
