import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal

db = SessionLocal()
billy = db.query(models.User).filter(models.User.id == '9615').first()

print(f"=== DETAILED KPI ANALYSIS FOR ANDREAS BILLY SUTANDI ({billy.full_name}) ===")

# 1. GitLab Commits
commits_count = db.query(models.RawGitLabCommit).filter(
    models.RawGitLabCommit.author_email.in_(['billyfebram@gmail.com', 'andreas.sutandi@atibusinessgroup.com'])
).count()
print(f"1. Total GitLab Commits: {commits_count} commits across repositories")

# GitLab repos
proj_commits = db.query(
    models.RawGitLabCommit.project_id
).filter(
    models.RawGitLabCommit.author_email.in_(['billyfebram@gmail.com', 'andreas.sutandi@atibusinessgroup.com'])
).distinct().all()

print("   GitLab Projects contributed to:")
for pc in proj_commits:
    p = db.query(models.Project).filter(models.Project.id == pc[0]).first()
    if p:
        cnt = db.query(models.RawGitLabCommit).filter(
            models.RawGitLabCommit.project_id == pc[0],
            models.RawGitLabCommit.author_email.in_(['billyfebram@gmail.com', 'andreas.sutandi@atibusinessgroup.com'])
        ).count()
        print(f"    - {p.project_name}: {cnt} commits")

# 2. Jira Issues
jira_issues = db.query(models.RawJiraIssue).filter(
    models.RawJiraIssue.assignee_account_id == '5de480fe3384720d1879bce3'
).all()
print(f"\n2. Total Jira Issues Assigned: {len(jira_issues)} issues in Jira")

proj_jira = {}
for ji in jira_issues:
    pkey = ji.issue_key.split('-')[0]
    proj_jira[pkey] = proj_jira.get(pkey, 0) + 1

print("   Jira Projects assigned:")
for pk, cnt in proj_jira.items():
    print(f"    - Jira Project {pk}: {cnt} issues")
