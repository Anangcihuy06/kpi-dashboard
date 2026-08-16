import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from datetime import datetime

db = SessionLocal()

nanang_jira = '5de71ecb8743750d00b7fbf5'
jiras = db.query(models.RawJiraIssue).filter(models.RawJiraIssue.assignee_account_id == nanang_jira).all()

from_date = datetime(2026, 1, 1)
to_date = datetime(2026, 12, 31, 23, 59, 59)

print("=== INSPECTING NANANG JIRA ISSUES EXTRACTING DATES FROM RAW_DATA JSON ===")
completed_statuses = ["done", "resolved", "ready to release", "ready for uat", "uat (user)", "ready for qa", "in qa"]

in_2026_cnt = 0
for ji in jiras:
    fields = ji.raw_data.get('fields', {}) if ji.raw_data else {}
    
    # Try resolutiondate, then updated, then created
    res_str = fields.get('resolutiondate') or fields.get('updated') or fields.get('created')
    status_str = fields.get('status', {}).get('name', ji.status)
    
    if res_str:
        try:
            # Parse ISO format (e.g. 2026-03-26T07:24:52.282+0700)
            clean_date = res_str.split('.')[0] # Remove milliseconds
            if 'T' in clean_date:
                dt = datetime.strptime(clean_date, "%Y-%m-%dT%H:%M:%S")
            else:
                dt = datetime.fromisoformat(clean_date.replace('Z', '+00:00'))
                
            if from_date <= dt <= to_date:
                if status_str.lower() in completed_statuses:
                    in_2026_cnt += 1
                    print(f"Key: {ji.issue_key:<10} | Status: {status_str:<15} | Date: {clean_date:<20} | Summary: {fields.get('summary', '')[:40]}")
        except Exception as e:
            pass

print(f"Total Strictly Completed Issues in 2026 using JSON dates: {in_2026_cnt}")
