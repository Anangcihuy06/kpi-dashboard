import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
import models
from yearly_kpi_engine import YearlyKPIEngine, get_rule_and_metrics_for_user

db = SessionLocal()
nanang = db.query(models.User).filter(models.User.full_name.ilike('%nanang%')).first()
ansha = db.query(models.User).filter(models.User.full_name.ilike('%ansha%')).first()

def check_user(u):
    print(f"\n=== {u.full_name} ===")
    print(f"User division_id={u.division_id}, supervisor_id={u.supervisor_id}")
    rule, metrics = get_rule_and_metrics_for_user(db, u)
    if not rule:
        print("No rule found!")
        return
        
    print(f"Rule ID: {rule.id}, Name: {rule.name}")
    print(f"Rule Division ID: {rule.division_id}, Rule Group ID: {rule.group_id}")
    
    for m in metrics:
        if m.metric_key == "feature_complexity" or "COMPLEXITY" in m.metric_key.upper():
            print(f"Metric: {m.metric_key}")
            print(f"  Variables: {m.variables}")

check_user(nanang)
check_user(ansha)
