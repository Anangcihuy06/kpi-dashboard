import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from comprehensive_sync import sync_user_comprehensive, calculate_daily_aggregated_kpi
from datetime import datetime, timedelta

db = SessionLocal()
setting = db.query(models.IntegrationSetting).first()
users = db.query(models.User).filter(models.User.is_active == True).all()

from_date = datetime(2026, 1, 1)
to_date = datetime(2026, 12, 31)

log_lines = [f"Starting full discovery sync for {len(users)} users..."]

for u in users:
    try:
        res = sync_user_comprehensive(db, u, setting, from_date, to_date)
        
        # Calculate daily aggregated KPIs for all days in 2026 for this user
        curr = from_date
        while curr <= to_date:
            calculate_daily_aggregated_kpi(db, u, curr)
            curr += timedelta(days=1)
            
        log_lines.append(f"User {u.full_name} ({u.id}): SUCCESS - {res.get('total_records', 0)} records")
    except Exception as e:
        log_lines.append(f"User {u.full_name} ({u.id}): ERROR - {e}")

with open('c:/Users/ATI-User/KPI-Dashboard/backend/sync_result.log', 'w', encoding='utf-8') as f:
    f.write("\n".join(log_lines))

db.close()
