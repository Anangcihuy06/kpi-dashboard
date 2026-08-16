from fastapi import APIRouter, Request, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from database import get_db
import logging
from datetime import datetime, timedelta
import models
from comprehensive_sync import sync_user_comprehensive

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])
logger = logging.getLogger("Webhooks")

@router.post("/gitlab")
async def gitlab_webhook(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Handle GitLab webhooks for pushes and merge requests.
    When a push or MR happens, we can trigger a targeted sync for the author.
    """
    payload = await request.json()
    event_type = request.headers.get("X-Gitlab-Event", "")
    
    logger.info(f"Received GitLab Webhook: {event_type}")
    
    if event_type == "Push Hook":
        commits = payload.get("commits", [])
        if commits:
            author_email = commits[0].get("author", {}).get("email")
            if author_email:
                user = db.query(models.User).filter(models.User.email == author_email).first()
                if user:
                    start_date = datetime.now() - timedelta(days=2)
                    end_date = datetime.now() + timedelta(days=1)
                    settings = db.query(models.IntegrationSetting).first()
                    background_tasks.add_task(sync_user_comprehensive, db, user, settings, start_date, end_date)
                    return {"status": "success", "message": f"Queued sync for user {user.full_name}"}

    return {"status": "success", "message": "Webhook processed"}


@router.post("/jira")
async def jira_webhook(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Handle Jira webhooks for issue updates and worklog updates.
    """
    payload = await request.json()
    event_type = payload.get("webhookEvent")
    
    logger.info(f"Received Jira Webhook: {event_type}")
    
    issue = payload.get("issue", {})
    fields = issue.get("fields", {})
    assignee = fields.get("assignee", {})
    
    if assignee:
        email = assignee.get("emailAddress")
        if email:
            user = db.query(models.User).filter(models.User.email == email).first()
            if user:
                start_date = datetime.now() - timedelta(days=2)
                end_date = datetime.now() + timedelta(days=1)
                settings = db.query(models.IntegrationSetting).first()
                background_tasks.add_task(sync_user_comprehensive, db, user, settings, start_date, end_date)
                return {"status": "success", "message": f"Queued sync for user {user.full_name}"}

    return {"status": "success", "message": "Webhook processed"}
