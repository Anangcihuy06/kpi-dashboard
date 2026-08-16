import sys
import os
sys.path.append(os.getcwd())
from database import SessionLocal
import models
from sync_service import get_system_token, fetch_all_subordinates_attendance
import datetime

db = SessionLocal()
token = get_system_token()
if not token:
    print("Failed to get token")
    sys.exit(1)

records_by_nik = fetch_all_subordinates_attendance(token, 2026)
users = db.query(models.User).all()
nik_to_user = {u.nik: u for u in users if u.nik}

for nik, records in records_by_nik.items():
    user = nik_to_user.get(nik)
    if not user:
        continue
    print(f"Saving {len(records)} attendance records for {user.full_name}...")
    for rec in records:
        raw_date = rec.get("clockIn") or rec.get("date") or ""
        if not raw_date:
            continue
        try:
            d_str = raw_date[:10] # YYYY-MM-DD
        except:
            continue
            
        existing = db.query(models.AttendanceRecord).filter(
            models.AttendanceRecord.user_id == user.id,
            models.AttendanceRecord.date == d_str
        ).first()
        
        remark = (rec.get("remarkText") or "").lower()
        is_late = "late" in remark
        
        if existing:
            existing.status = "Present"
            existing.is_late = is_late
        else:
            att = models.AttendanceRecord(
                user_id=user.id,
                date=d_str,
                status="Present",
                is_late=is_late
            )
            db.add(att)

db.commit()
print("Attendance saved.")
