import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal

db = SessionLocal()

issues = db.query(models.RawJiraIssue).filter(models.RawJiraIssue.resolved_date.isnot(None)).all()

print(f"Normalizing {len(issues)} Jira issues in database...")
updated_cnt = 0
for ji in issues:
    if ji.status != "Done":
        # Keep track of old status
        old_status = ji.status
        ji.status = "Done"
        
        # Update raw_data fields if it exists
        if ji.raw_data and 'fields' in ji.raw_data:
            ji.raw_data['fields']['status'] = {'name': 'Done'}
            
        updated_cnt += 1

db.commit()
print(f"Normalization complete! Successfully updated {updated_cnt} issues to 'Done' status.")
