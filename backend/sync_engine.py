import json
from datetime import datetime
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

def update_job_progress(db: Session, job_id: str, progress: int, status: str = "RUNNING"):
    """Update job progress safely"""
    job = db.query(models.SyncJob).filter(models.SyncJob.id == job_id).first()
    if job:
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

def get_job_status(db: Session, job_id: str):
    """Get the status of a specific job"""
    job = db.query(models.SyncJob).filter(models.SyncJob.id == job_id).first()
    if not job:
        return None
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
