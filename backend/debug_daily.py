import sqlite3
from database import SessionLocal
import models
from datetime import datetime

db = SessionLocal()
nanang = db.query(models.User).filter(models.User.full_name.like('%Nanang%')).first()
date = datetime.strptime("2026-05-13", "%Y-%m-%d")

date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)

activities = db.query(models.Activity).filter(
    models.Activity.user_id == nanang.id,
    models.Activity.activity_date >= date_start,
    models.Activity.activity_date <= date_end
).all()

print(f"Found {len(activities)} activities for 2026-05-13")
sp_total = 0.0
for activity in activities:
    print(f"Activity ID: {activity.id}, Type: {activity.activity_type}, SP: {activity.story_points}")
    if activity.source == 'jira' and activity.activity_type in ['issue_done', 'issue_completed']:
        sp = activity.story_points
        if not sp and activity.activity_metadata:
            sp = activity.activity_metadata.get("story_points", 0)
        print(f" -> Evaluated SP: {sp}")
        if sp:
            sp_total += float(sp)

print(f"Total calculated SP: {sp_total}")
