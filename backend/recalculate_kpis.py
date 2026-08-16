from database import SessionLocal
import models
from sync_service import sync_yearly_user_metrics
import datetime

db = SessionLocal()
users = db.query(models.User).all()
settings = db.query(models.IntegrationSetting).first()

for user in users:
    # Delete existing daily KPIs to force recalculation
    db.query(models.KPIEmployeeDaily).filter(
        models.KPIEmployeeDaily.user_id == user.id,
        models.KPIEmployeeDaily.date >= '2026-01-01',
        models.KPIEmployeeDaily.date <= '2026-12-31'
    ).delete()
    db.commit()
    
    # Recalculate
    print(f"Recalculating for {user.full_name}")
    sync_yearly_user_metrics(db, user, 2026, settings)
    
print("Done recalculating all KPIs.")
