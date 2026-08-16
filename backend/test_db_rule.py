import sys
import os
sys.path.append(os.getcwd())
from database import SessionLocal
import models
db = SessionLocal()
metrics = db.query(models.KPIRuleMetric).filter(models.KPIRuleMetric.metric_key == 'feature_complexity').all()
for m in metrics:
    print(f"Rule: {m.rule_id}, Weight: {m.weight}, Target: {m.target_value}, Formula: {m.custom_formula}")
