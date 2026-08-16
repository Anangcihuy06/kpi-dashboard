import sys
import os
sys.path.append(os.getcwd())
from database import SessionLocal
import models

db = SessionLocal()
records = db.query(models.AttendanceRecord).filter(models.AttendanceRecord.user_id == '6518').all()
statuses = set()
for r in records:
    statuses.add(r.status)
print("Statuses in DB:", statuses)
