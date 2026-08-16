import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal

db = SessionLocal()

billy_acts = db.query(models.Activity).filter(models.Activity.user_id == '9615').all()

print(f"=== ALL ACTIVITIES FOR ANDREAS BILLY SUTANDI ({len(billy_acts)} total) ===")

jira_acts = [a for a in billy_acts if a.source == 'jira']
gitlab_acts = [a for a in billy_acts if a.source == 'gitlab']

print(f"GitLab Activities: {len(gitlab_acts)} (Commits/MRs)")
print(f"Jira Activities: {len(jira_acts)}")

sp_by_jira_project = {}
for a in jira_acts:
    meta = a.activity_metadata or {}
    pkey = meta.get('jira_project_key') or (a.reference_id.split('-')[0] if '-' in a.reference_id else 'UNKNOWN')
    sp = a.story_points or 0.0
    sp_by_jira_project[pkey] = sp_by_jira_project.get(pkey, 0.0) + sp

print("\nJira Story Points breakdown by Jira Project for Billy:")
for pkey, sp_sum in sp_by_jira_project.items():
    print(f" - Project {pkey}: {sp_sum} SP")

print("\nTop 15 Highest Story Point Jira Issues for Billy:")
sorted_jira = sorted(jira_acts, key=lambda x: x.story_points or 0.0, reverse=True)
for a in sorted_jira[:15]:
    meta = a.activity_metadata or {}
    print(f"   * {a.reference_id} | SP: {a.story_points} | Summary: {meta.get('issue_summary')}")
