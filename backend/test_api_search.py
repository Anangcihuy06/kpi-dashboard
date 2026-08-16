import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
import models
from utils.security import decrypt_val
import requests

db = SessionLocal()
settings = db.query(models.IntegrationSetting).first()
if settings and settings.gitlab_token_encrypted:
    gitlab_token = decrypt_val(settings.gitlab_token_encrypted)
    gitlab_url = settings.gitlab_url.rstrip("/")
    headers = {"PRIVATE-TOKEN": gitlab_token}
    
    user_search_url = f"{gitlab_url}/api/v4/users"
    params = {"search": "Nanang Wahyudi"}
    response = requests.get(user_search_url, headers=headers, params=params, timeout=10)
    print(f"GitLab status: {response.status_code}")
    print(f"GitLab response: {response.text}")
else:
    print("No settings")

if settings and settings.jira_token_encrypted:
    jira_email = settings.jira_admin_email
    jira_token = decrypt_val(settings.jira_token_encrypted)
    jira_url = settings.jira_url.rstrip("/")
    from requests.auth import HTTPBasicAuth
    jira_auth = HTTPBasicAuth(jira_email, jira_token)
    
    user_search_url = f"{jira_url}/rest/api/3/user/search"
    params = {"query": "Nanang Wahyudi"}
    response = requests.get(user_search_url, auth=jira_auth, params=params, timeout=10)
    print(f"Jira Name status: {response.status_code}")
    print(f"Jira Name response: {response.text}")
    
    params = {"query": "nanang.wahyudi@atibusinessgroup.com"}
    response = requests.get(user_search_url, auth=jira_auth, params=params, timeout=10)
    print(f"Jira Email status: {response.status_code}")
    print(f"Jira Email response: {response.text}")
