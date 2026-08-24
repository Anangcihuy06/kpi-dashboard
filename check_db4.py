import sys
sys.path.insert(0, './backend')
from database import SessionLocal
import models
db = SessionLocal()
records = db.query(models.AttendanceRecord).filter(
    models.AttendanceRecord.date.like('2026%')
).limit(10).all()
for r in records:
    print(f"Date: {r.date}, User: {r.user_id}, Status: {r.status}, Late: {r.is_late}")
