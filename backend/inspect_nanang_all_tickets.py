import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from datetime import datetime

db = SessionLocal()

nanang_jira = '5de71ecb8743750d00b7fbf5'
jiras = db.query(models.RawJiraIssue).filter(models.RawJiraIssue.assignee_account_id == nanang_jira).all()

print(f"=== ALL RAW JIRA ISSUES FOR NANANG WAHYUDI (Total in DB: {len(jiras)}) ===")
print(f"{'Key':<10} | {'Status':<15} | {'Resolved Date':<25} | {'Updated Date':<25} | {'Created Date':<25} | {'Summary'}")
print("-" * 130)
for ji in jiras:
    print(f"{ji.issue_key:<10} | {ji.status:<15} | {str(ji.resolved_date):<25} | {str(ji.updated_date):<25} | {str(ji.created_date):<25} | {ji.raw_data.get('fields', {}).get('summary', ji.issue_key)[:30]}")
