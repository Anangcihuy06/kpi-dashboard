import sys
import os
sys.path.append(os.getcwd())
from database import SessionLocal
import models
import comprehensive_sync
from sync_service import sync_yearly_user_metrics

# Monkey patch GitLab sync to bypass it and avoid crashes
comprehensive_sync.sync_gitlab_commits = lambda *args, **kwargs: 0
comprehensive_sync.sync_gitlab_merge_requests = lambda *args, **kwargs: 0

db = SessionLocal()
users = db.query(models.User).filter(models.User.is_active == True).all()
settings = db.query(models.IntegrationSetting).first()

print("Forcing recalculation (bypassing GitLab)...")
for user in users:
    print(f"Recalculating {user.full_name}...")
    try:
        sync_yearly_user_metrics(db, user, 2026, settings)
    except Exception as e:
        print(f"Error on {user.full_name}: {e}")

print("Done recalculating.")
