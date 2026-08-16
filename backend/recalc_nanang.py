import sys
import os
sys.path.append(os.getcwd())
import comprehensive_sync
comprehensive_sync.sync_gitlab_commits = lambda *args, **kwargs: 0
comprehensive_sync.sync_gitlab_merge_requests = lambda *args, **kwargs: 0

from database import SessionLocal
import models
from sync_service import sync_yearly_user_metrics

db = SessionLocal()
user = db.query(models.User).filter(models.User.nik == '01.04.19.1905').first()
settings = db.query(models.IntegrationSetting).first()

print(f"Recalculating for {user.full_name}")
# First clear old KPI data
db.query(models.KPIEmployeeDaily).filter(
    models.KPIEmployeeDaily.user_id == user.id,
    models.KPIEmployeeDaily.date >= '2026-01-01',
    models.KPIEmployeeDaily.date <= '2026-12-31'
).delete()
db.commit()

sync_yearly_user_metrics(db, user, 2026, settings)
print("Done")
