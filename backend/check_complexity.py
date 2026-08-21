import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
import models
from feature_analyzer import analyze_multi_factor, DEFAULT_FEATURE_CONFIG
import json

db = SessionLocal()

subs = db.query(models.User).filter(models.User.supervisor_id == "1276").all()
for sub in subs:
    ident = db.query(models.EmployeeIdentity).filter(
        models.EmployeeIdentity.user_id == sub.id,
        models.EmployeeIdentity.source == 'jira'
    ).first()
    
    if ident and ident.external_user_id:
        issue = db.query(models.RawJiraIssue).filter(
            models.RawJiraIssue.assignee_account_id == ident.external_user_id,
            models.RawJiraIssue.status.ilike('%done%')
        ).first()
        
        if issue:
            print(f"\nSubordinate: {sub.full_name}")
            print(f"Jira Issue: {issue.issue_key} - {issue.summary}")
            
            # get raw data
            issue_data = issue.raw_data
            if isinstance(issue_data, str):
                issue_data = json.loads(issue_data)
                
            res = analyze_multi_factor(issue_data, config=DEFAULT_FEATURE_CONFIG)
            
            print(f"Complexity Score: {res['kpi_points']}")
            print("Breakdown:")
            print(f"  - Technical Complexity: {res['technical_complexity']}")
            print(f"  - Business Impact: {res['business_impact']}")
            print(f"  - System Scope: {res['system_scope']}")
            print(f"  - Delivery Risk: {res['delivery_risk']}")
            print(f"  - Ownership Level: {res['ownership_level']}")
            print(f"  - Total Score: {res['total_score']}")
            
            break
