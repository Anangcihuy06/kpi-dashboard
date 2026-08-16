import sys
import os
sys.path.append(os.getcwd())
from sync_service import get_system_token, fetch_all_subordinates_attendance
from database import SessionLocal
import models
from datetime import datetime

token = get_system_token()
if not token:
    print("Failed to get token")
    sys.exit(1)

records_by_nik = fetch_all_subordinates_attendance(token, 2026)
db = SessionLocal()

for user in db.query(models.User).filter(models.User.is_active == True).all():
    records = records_by_nik.get(user.nik, [])
    if not records:
        continue
    
    for rec in records:
        raw_date = rec.get("clockin_time") or rec.get("clockIn") or rec.get("date") or ""
        if not raw_date:
            continue
            
        try:
            d_str = raw_date[:10]
            d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
        except:
            continue
            
        existing = db.query(models.AttendanceRecord).filter(
            models.AttendanceRecord.user_id == user.id,
            models.AttendanceRecord.date == d_obj
        ).first()
        
        remark = (rec.get("remarkText") or "").lower()
        is_late = "late" in remark
        
        if existing:
            existing.status = "PRESENT"
            existing.is_late = is_late
        else:
            default_sprint = db.query(models.Sprint).first()
            sprint_id = default_sprint.id if default_sprint else "cd7c558a-dfb9-49b9-8438-5b7f58aae49f"
            att = models.AttendanceRecord(
                user_id=user.id,
                date=d_obj,
                status="PRESENT",
                is_late=is_late,
                sprint_id=sprint_id
            )
            db.add(att)
    
    try:
        db.commit()
    except Exception as e:
        print(f"Error saving {user.full_name}: {e}")
        db.rollback()

print("Attendance saved properly.")
