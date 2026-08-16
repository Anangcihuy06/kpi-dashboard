import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import random
from datetime import datetime, timedelta
import models
from database import SessionLocal

db = SessionLocal()
users = db.query(models.User).filter(models.User.is_active == True).all()

# Get a valid default sprint ID
default_sprint = db.query(models.Sprint).first()
sprint_id = default_sprint.id if default_sprint else "cd7c558a-dfb9-49b9-8438-5b7f58aae49f"

# Dates range for 2025
start_2025 = datetime(2025, 1, 1)
end_2025 = datetime(2025, 12, 31)

print(f"=== SEEDING AUTHENTIC ATTENDANCE & LATE RECORDS FOR 2025 ({len(users)} users) ===")

# Delete existing 2025 attendance records
db.query(models.AttendanceRecord).filter(
    models.AttendanceRecord.date >= '2025-01-01',
    models.AttendanceRecord.date <= '2025-12-31'
).delete(synchronize_session=False)

random.seed(42)  # Consistent reproducible seed

user_late_rates = {
    '6518': 0.05,  # Nanang: ~13 days late
    '9615': 0.12,  # Billy: ~31 days late
    '7690': 0.10,  # Adian: ~26 days late
    '6856': 0.09,  # Bayu: ~23 days late
    '6592': 0.10,  # Imamul: ~26 days late
    '7052': 0.11,  # Fadli: ~28 days late
    '7724': 0.08,  # Ansha: ~20 days late
    '6182': 0.04,  # Novrizal: ~10 days late
}

added_count = 0
late_total = 0

curr = start_2025
while curr <= end_2025:
    if curr.weekday() < 5:  # Mon-Fri
        date_str = curr.strftime("%Y-%m-%d")
        for u in users:
            late_rate = user_late_rates.get(u.id, 0.08)
            is_late = random.random() < late_rate
            
            late_mins = random.randint(5, 45) if is_late else 0
            clock_in = f"09:{late_mins:02d}:00" if is_late else f"08:{random.randint(45, 59):02d}:00"
            
            rec = models.AttendanceRecord(
                user_id=u.id,
                sprint_id=sprint_id,
                date=date_str,
                status="LATE" if is_late else "PRESENT",
                is_late=is_late,
                late_minutes=late_mins,
                clock_in=clock_in,
                clock_out="17:30:00"
            )
            db.add(rec)
            added_count += 1
            if is_late:
                late_total += 1
                
    curr += timedelta(days=1)

db.commit()
print(f"SUCCESSFULLY SEEDED {added_count} ATTENDANCE RECORDS FOR 2025 ({late_total} LATE RECORDS)!")
