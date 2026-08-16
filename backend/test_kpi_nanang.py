import sys
import os
sys.path.append(os.getcwd())
from database import SessionLocal
import models
from engine import DynamicKPIEngine

db = SessionLocal()
# Nanang
user = db.query(models.User).filter(models.User.nik == '01.05.13.500').first()
# Find a 2026 sprint
sprint = db.query(models.Sprint).filter(models.Sprint.start_date >= '2026-01-01').first()

result = DynamicKPIEngine.calculate_sprint_score(db, user, sprint)
import json
print(json.dumps(result, indent=2))
