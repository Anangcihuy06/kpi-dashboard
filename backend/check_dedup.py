from database import SessionLocal
from models import KPIEmployeeDaily, User

db = SessionLocal()
user = db.query(User).filter(User.nik == '18.11.22.3063').first()
kpis = db.query(KPIEmployeeDaily).filter(KPIEmployeeDaily.user_id == user.id, KPIEmployeeDaily.date >= '2026-01-01').all()
dates = set()
total = 0
for k in kpis:
    # Handle datetime or string
    if hasattr(k.date, 'strftime'):
        k_d = k.date.strftime('%Y-%m-%d')
    else:
        k_d = str(k.date).split()[0]
    
    if k_d not in dates:
        dates.add(k_d)
        total += k.attendance_days

print("total deduplicated:", total)
