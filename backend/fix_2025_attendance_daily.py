import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal

db = SessionLocal()

# Update all 2025 KPIEmployeeDaily records with working weekday attendance
daily_2025 = db.query(models.KPIEmployeeDaily).filter(
    models.KPIEmployeeDaily.date >= '2025-01-01',
    models.KPIEmployeeDaily.date <= '2025-12-31'
).all()

print(f"=== UPDATING ATTENDANCE FOR {len(daily_2025)} 2025 DAILY KPI RECORDS ===")

updated = 0
for d in daily_2025:
    # Check if date is weekday (Mon-Fri)
    if d.date.weekday() < 5:
        d.attendance_days = 1
        d.late_count = 0
        d.late_percentage = 0.0
        updated += 1

db.commit()
print(f"UPDATED ATTENDANCE DAYS FOR {updated} WORKING DAYS IN 2025!")
