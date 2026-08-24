import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from sqlalchemy.orm import Session
from database import SessionLocal
import models
from yearly_kpi_engine import get_rule_and_metrics_for_user

def check():
    db = SessionLocal()
    subs = db.query(models.User).filter(models.User.id.in_(['api_7187', 'api_9303'])).all()
    for sub in subs:
        rule, metrics = get_rule_and_metrics_for_user(db, sub)
        print(f"{sub.full_name}: rule={rule.id if rule else 'None'}, division={sub.division_id}, group={sub.group_id}")
        if metrics:
            print(f"  Metrics count: {len(metrics)}")
        else:
            print("  No metrics definitions found.")

if __name__ == "__main__":
    check()
