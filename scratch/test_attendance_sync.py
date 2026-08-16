import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from database import SessionLocal
import models
from sync_service import sync_attendance_for_year
from comprehensive_sync import sync_user_comprehensive
from datetime import datetime

db = SessionLocal()

nanang = db.query(models.User).filter(models.User.nik == "01.04.19.1905").first()

if not nanang:
    print("Nanang not found")
else:
    print(f"Syncing attendance for Nanang {nanang.full_name}...")
    res = sync_attendance_for_year(db, [nanang], 2026)
    print("Result:")
    print(res)

    # Let's check his KPIEmployeeDaily for 2026
    start_date = datetime(2026, 1, 1)
    end_date = datetime(2026, 12, 31)
    
    kpis = db.query(models.KPIEmployeeDaily).filter(
        models.KPIEmployeeDaily.user_id == nanang.id,
        models.KPIEmployeeDaily.date >= start_date,
        models.KPIEmployeeDaily.date <= end_date
    ).all()
    
    total_att = sum([k.attendance_days for k in kpis])
    total_late = sum([k.late_count for k in kpis])
    
    print(f"KPIEmployeeDaily Total Attendance 2026: {total_att}")
    print(f"KPIEmployeeDaily Total Late 2026: {total_late}")

db.close()
