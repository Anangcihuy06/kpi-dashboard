import sys
import os
sys.path.append(os.getcwd())
from database import SessionLocal
import models
from sqlalchemy import and_

db = SessionLocal()
dates = db.query(models.KPIEmployeeDaily.date, models.KPIEmployeeDaily.attendance_days, models.KPIEmployeeDaily.late_count).filter(
    and_(
        models.KPIEmployeeDaily.user_id == '6518',
        models.KPIEmployeeDaily.date >= '2026-01-01',
        models.KPIEmployeeDaily.date <= '2026-12-31'
    )
).order_by(models.KPIEmployeeDaily.date).all()

count = 0
for d in dates:
    print(d)
    count += 1
print(f"Total rows: {count}")
