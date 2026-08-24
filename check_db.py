import sys
sys.path.insert(0, './backend')
from database import SessionLocal
import models
db = SessionLocal()
records = db.query(models.AttendanceRecord).filter(models.AttendanceRecord.date.like('2026%')).count()
print(f"Total AttendanceRecord for 2026: {records}")
