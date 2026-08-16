import sys
import os
import requests
sys.path.append(os.getcwd())
from database import SessionLocal
import models

db = SessionLocal()
settings = db.query(models.IntegrationSetting).first()
jira_auth = (settings.jira_email, settings.jira_token) # No wait, it's encrypted!
