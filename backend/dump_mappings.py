import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
import models

db = SessionLocal()

users = db.query(models.User).filter(models.User.is_active == True).all()

mapping = {}
for u in users:
    mapping[u.full_name] = {
        "nik": u.nik,
        "jira_account_id": u.jira_account_id,
        "gitlab_username": u.gitlab_username
    }

print(json.dumps(mapping, indent=2))
