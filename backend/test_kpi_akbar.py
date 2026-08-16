import sys
import os
sys.path.append(os.getcwd())
from database import SessionLocal
import models
from engine import DynamicKPIEngine

db = SessionLocal()
akbar = db.query(models.User).filter(models.User.full_name.like('%Akbar%')).first()
sprint = db.query(models.Sprint).filter(models.Sprint.sprint_name == 'F20M-27').first()

if not akbar or not sprint:
    print("Not found")
    sys.exit(1)

engine = DynamicKPIEngine(db)
result = engine.calculate_kpi(akbar.id, sprint.id)
import json
print(json.dumps(result, indent=2))
