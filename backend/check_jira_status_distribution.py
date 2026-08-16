import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal

db = SessionLocal()

issues = db.query(models.RawJiraIssue).all()

status_counts = {}
for ji in issues:
    status_counts[ji.status] = status_counts.get(ji.status, 0) + 1

print("=== JIRA ISSUE STATUS DISTRIBUTION IN DATABASE ===")
for status, count in status_counts.items():
    print(f"Status: {status:<15} | Count: {count}")
