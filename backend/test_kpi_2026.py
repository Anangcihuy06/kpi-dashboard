import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from sqlalchemy import func

db = SessionLocal()
user = db.query(models.User).filter(models.User.full_name.ilike('%Nanang%')).first()

kpis = db.query(
    func.sum(models.KPIEmployeeDaily.issue_completed).label('issues'),
    func.sum(models.KPIEmployeeDaily.story_points_completed).label('sp')
).filter(
    models.KPIEmployeeDaily.user_id == user.id,
    func.extract('year', models.KPIEmployeeDaily.date) == 2026
).first()

print(f"Nanang 2026 KPIs -> Issues: {kpis.issues}, SP: {kpis.sp}")
