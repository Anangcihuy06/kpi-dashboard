from database import SessionLocal
import models
from datetime import datetime

db = SessionLocal()
from_date = datetime.strptime("2026-01-01", "%Y-%m-%d")
to_date = datetime.strptime("2026-12-31", "%Y-%m-%d")
user = db.query(models.User).filter(models.User.id == '6518').first()

daily_kpis = db.query(models.KPIEmployeeDaily).filter(
    models.KPIEmployeeDaily.user_id == user.id,
    models.KPIEmployeeDaily.date >= from_date,
    models.KPIEmployeeDaily.date <= to_date
).order_by(models.KPIEmployeeDaily.date).all()

print(f"Found {len(daily_kpis)} records")
total_commits = 0
total_issues = 0
for daily in daily_kpis:
    total_commits += daily.commit_count
    total_issues += daily.issue_completed
print(f"Commits: {total_commits}, Issues: {total_issues}")
