import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from datetime import datetime
import json
import random

db = SessionLocal()

# We want to distribute about 30% of completed JIRA issues for each user into 2025.
# Let's define the dates in 2025 to assign:
dates_2025 = [
    ("2025-03-12 10:24:52.282000", "2025-03-12T10:24:52.282+0700"),
    ("2025-06-18 14:15:30.115000", "2025-06-18T14:15:30.115+0700"),
    ("2025-09-22 09:44:08.561000", "2025-09-22T09:44:08.561+0700"),
    ("2025-11-05 16:30:12.782000", "2025-11-05T16:30:12.782+0700")
]

users = db.query(models.User).filter(models.User.is_active == True).all()

print("=== DISTRIBUTING MOCK JIRA TASKS INTO YEAR 2025 ===")
total_updated = 0

for u in users:
    j_ident = db.query(models.EmployeeIdentity).filter(
        models.EmployeeIdentity.user_id == u.id,
        models.EmployeeIdentity.source == 'jira'
    ).first()
    
    if not j_ident or not j_ident.external_user_id:
        continue
        
    jiras = db.query(models.RawJiraIssue).filter(
        models.RawJiraIssue.assignee_account_id == j_ident.external_user_id
    ).all()
    
    if not jiras:
        continue
        
    # Shuffle issues and select 30% of them
    random.seed(42)  # For reproducibility
    issues_to_shift = random.sample(jiras, int(len(jiras) * 0.35))
    
    print(f"User: {u.full_name:<30} | Total Issues: {len(jiras):<3} | Shifting {len(issues_to_shift)} to 2025")
    
    for i, ji in enumerate(issues_to_shift):
        db_date_str, json_date_str = dates_2025[i % len(dates_2025)]
        
        # Parse datetime
        dt = datetime.fromisoformat(db_date_str)
        
        # Update columns
        ji.resolved_date = dt
        ji.updated_date = dt
        ji.created_date = dt
        
        # Update raw_data json fields
        if ji.raw_data and 'fields' in ji.raw_data:
            ji.raw_data['fields']['resolutiondate'] = json_date_str
            ji.raw_data['fields']['updated'] = json_date_str
            ji.raw_data['fields']['created'] = json_date_str
            
        total_updated += 1

db.commit()
print(f"\nSuccessfully distributed {total_updated} Jira issues into the year 2025!")
