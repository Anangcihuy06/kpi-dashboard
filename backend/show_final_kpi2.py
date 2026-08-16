import sys
import os
sys.path.append(os.getcwd())
from database import SessionLocal
import models
from datetime import datetime

db = SessionLocal()
kpi = db.query(models.KPIEmployeeDaily).filter(
    models.KPIEmployeeDaily.user_id == '6518'
).order_by(models.KPIEmployeeDaily.date.desc()).first()

print(f"Attendance Days: {kpi.attendance_days}")
print(f"Late Count: {kpi.late_count}")
print(f"Overall Score: {kpi.overall_score}")
