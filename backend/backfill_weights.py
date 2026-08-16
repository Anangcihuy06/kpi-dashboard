import sqlite3
from database import SessionLocal
import models
from feature_analyzer import calculate_feature_weight
import json

db = SessionLocal()
activities = db.query(models.Activity).filter(models.Activity.activity_type == 'issue_completed').all()

updated = 0
for act in activities:
    # We need the raw issue data to pass to calculate_feature_weight
    # But Activity doesn't store raw issue. We can fetch it from RawJiraIssue
    raw_issue = db.query(models.RawJiraIssue).filter(models.RawJiraIssue.issue_key == act.reference_id).first()
    if raw_issue and raw_issue.raw_data:
        weight = calculate_feature_weight(raw_issue.raw_data)
        act.story_points = weight
        # Update metadata too
        meta = act.activity_metadata or {}
        meta['feature_weight'] = weight
        act.activity_metadata = meta
        updated += 1

db.commit()
print(f"Updated {updated} activities with new feature weights.")
