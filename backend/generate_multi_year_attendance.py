import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from datetime import datetime, timedelta

db = SessionLocal()
users = db.query(models.User).filter(models.User.is_active == True).all()

# Generate Attendance Records for 2025 (261 working days)
start_2025 = datetime(2025, 1, 1)
end_2025 = datetime(2025, 12, 31)

print(f"=== GENERATING 2025 ATTENDANCE RECORDS FOR {len(users)} USERS ===")

att_created = 0
curr = start_2025
while curr <= end_2025:
    if curr.weekday() < 5:  # Mon-Fri
        date_str = curr.strftime("%Y-%m-%d")
        for u in users:
            existing = db.query(models.AttendanceRecord).filter(
                models.AttendanceRecord.user_id == u.id,
                models.AttendanceRecord.date == curr.date()
            ).first()
            
            if not existing:
                att_rec = models.AttendanceRecord(
                    user_id=u.id,
                    nik=u.nik or f"NIK-{u.id}",
                    full_name=u.full_name,
                    date=curr.date(),
                    status="PRESENT",
                    is_late=False,
                    late_minutes=0
                )
                db.add(att_rec)
                att_created += 1
    curr += timedelta(days=1)

db.commit()
print(f"CREATED {att_created} ATTENDANCE RECORDS FOR 2025!")
