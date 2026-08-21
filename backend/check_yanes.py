import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
import models
from datetime import datetime
from yearly_kpi_engine import get_rule_and_metrics_for_user

db = SessionLocal()
yanes = db.query(models.User).filter(models.User.full_name.ilike('%yanes%')).first()
if yanes:
    print(f"Yanes: {yanes.id} - {yanes.full_name}")
    subs = db.query(models.User).filter(models.User.supervisor_id == yanes.id).all()
    for sub in subs:
        print(f"  Sub: {sub.id} - {sub.full_name}")
        
        # Get KPI scores for this sub
        scores = db.query(models.KPIEmployeeDaily).filter(
            models.KPIEmployeeDaily.user_id == sub.id
        ).all()
        print(f"    Total KPI days: {len(scores)}")
        
        # Get identity
        ident = db.query(models.EmployeeIdentity).filter(
            models.EmployeeIdentity.user_id == sub.id,
            models.EmployeeIdentity.source == 'jira'
        ).first()
        
        if ident and ident.external_user_id:
            issues = db.query(models.RawJiraIssue).filter(
                models.RawJiraIssue.assignee_account_id == ident.external_user_id
            ).all()
            complexities = [i.complexity_score for i in issues if i.complexity_score is not None]
            print(f"    Total issues: {len(issues)}, issues with complexity: {len(complexities)}")
            if complexities:
                print(f"    Avg complexity: {sum(complexities)/len(complexities)}")
else:
    print("Yanes not found")
