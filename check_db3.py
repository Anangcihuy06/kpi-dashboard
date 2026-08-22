import sys
sys.path.insert(0, './backend')
from database import SessionLocal
import models
db = SessionLocal()
records = db.query(models.AttendanceRecord.user_id).filter(
    models.AttendanceRecord.date.like('2026%')
).distinct().all()
print(f"Users with AttendanceRecord for 2026: {[r[0] for r in records]}")
