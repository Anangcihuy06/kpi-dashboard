import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from comprehensive_sync import calculate_daily_aggregated_kpi
from datetime import datetime, timedelta

db = SessionLocal()
users = db.query(models.User).all()

start_date = datetime(2026, 1, 1)
end_date = datetime(2026, 12, 31)

print(f"Recalculating daily KPIs for {len(users)} users from {start_date.date()} to {end_date.date()}...")

for user in users:
    current_date = start_date
    updated_days = 0
    while current_date <= end_date:
        calculate_daily_aggregated_kpi(db, user, current_date)
        current_date += timedelta(days=1)
        updated_days += 1
    print(f"Done user {user.id} ({user.full_name}): recalculated {updated_days} days!")

print("\nALL DAILY KPIS RECALCULATED SUCCESSFULLY!")
