import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
import models
db = SessionLocal()
rules = db.query(models.KPIRule).filter(models.KPIRule.division_id == '23', models.KPIRule.group_id == '496').all()
for r in rules:
    active = r.is_active if hasattr(r, 'is_active') else 'No is_active column'
    print(f"Rule ID: {r.id}, Name: {r.name}, Active: {active}")
    for m in r.metrics:
        if "COMPLEXITY" in m.metric_key.upper():
            print(f"  Target: {m.variables.get('target_complexity_pts')}")
