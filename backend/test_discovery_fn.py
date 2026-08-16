import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from comprehensive_sync import discover_all_gitlab_projects

db = SessionLocal()
setting = db.query(models.IntegrationSetting).first()

projects = discover_all_gitlab_projects(db, setting)
db_projs = db.query(models.Project).filter(models.Project.source == 'gitlab').all()

with open('c:/Users/ATI-User/KPI-Dashboard/backend/discovery_result.txt', 'w', encoding='utf-8') as f:
    f.write(f"Total GitLab projects registered in DB: {len(db_projs)}\n\n")
    for p in db_projs:
        f.write(f" - ID {p.external_project_id}: {p.project_name} | {p.project_url}\n")
