import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
import models
db = SessionLocal()

def check_user(user_id):
    ident = db.query(models.EmployeeIdentity).filter_by(user_id=user_id, source='jira').first()
    jiras = db.query(models.RawJiraIssue).filter_by(assignee_account_id=ident.external_user_id).all()
    print(f"User {user_id}: {len(jiras)} issues")
    for j in jiras:
        print(f"  {j.issue_key}: SP={j.story_points}, Complexity={j.complexity_score}")

check_user("api_7187")
check_user("api_9303")
