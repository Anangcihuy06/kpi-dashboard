import sys
import os
sys.path.append(os.getcwd())
from database import SessionLocal
import models
from datetime import datetime

db = SessionLocal()
kpi = db.query(models.KPIEmployeeDaily).filter(
    models.KPIEmployeeDaily.user_id == '6518',
    models.KPIEmployeeDaily.date == '2026-12-31'
).first()

print(f"Attendance Days: {kpi.attendance_days}")
print(f"Late Count: {kpi.late_count}")
print(f"Feature Complexity Pts: {kpi.kpi_breakdown[0].get('actual_value')}")
print(f"Overall Score: {kpi.overall_score}")
