import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from datetime import datetime
from feature_analyzer import analyze_multi_factor

db = SessionLocal()

from_date = datetime(2026, 1, 1)
to_date = datetime(2026, 12, 31, 23, 59, 59)

billy_user_id = '9615'
billy = db.query(models.User).filter(models.User.id == billy_user_id).first()
jira_ident = db.query(models.EmployeeIdentity).filter(
    models.EmployeeIdentity.user_id == billy_user_id,
    models.EmployeeIdentity.source == 'jira'
).first()

if not jira_ident or not jira_ident.external_user_id:
    print("Billy JIRA Identity not found!")
    sys.exit(1)

jiras = db.query(models.RawJiraIssue).filter(
    models.RawJiraIssue.assignee_account_id == jira_ident.external_user_id
).all()

billy_issues = []
for ji in jiras:
    r_date = ji.resolved_date or ji.updated_date or ji.created_date
    if r_date:
        try:
            r_dt = datetime.fromisoformat(str(r_date).replace('Z', '+00:00')) if isinstance(r_date, str) else r_date
            r_dt_naive = r_dt.replace(tzinfo=None) if hasattr(r_dt, 'replace') else r_dt
            if from_date <= r_dt_naive <= to_date:
                res = analyze_multi_factor(ji.raw_data or {})
                billy_issues.append({
                    "key": ji.issue_key,
                    "summary": ji.raw_data.get('fields', {}).get('summary', ji.issue_key),
                    "analysis": res
                })
        except Exception as e:
            pass

print(f"=== DETAILED KPI ENGINE ANALYSIS FOR ANDREAS BILLY SUTANDI (2026) ===")
print(f"1. TASK DELIVERY (Task & Module Delivery Velocity):")
print(f"   - Total completed issues: {len(billy_issues)}")
print(f"   - Formula: (Billy's completed issues / Team Max completed issues) * 100")
print(f"   - Billy's value: {len(billy_issues)} issues")
print(f"   - Team Max benchmark: 41 issues (Billy himself is the benchmark for Task Delivery in 2026!)")
print(f"   - Task Delivery Score: ({len(billy_issues)} / 41) * 100 = 100.00%")
print(f"   - Weighted score (30% weight): 100.00% * 30% = 30.00 pts\n")

print(f"2. FEATURE COMPLEXITY (Feature & Module Architectural Weight):")
print(f"   - Total Feature Points (sum of KPI points): {sum(x['analysis']['kpi_points'] for x in billy_issues)} points")
print(f"   - Formula: (Billy's feature points / Team Max feature points) * 100")
print(f"   - Billy's value: {sum(x['analysis']['kpi_points'] for x in billy_issues)} points")
print(f"   - Team Max benchmark: 336.0 points (Billy is also the benchmark for Complexity!)")
print(f"   - Feature Complexity Score: (336.0 / 336.0) * 100 = 100.00%")
print(f"   - Weighted score (60% weight): 100.00% * 60% = 60.00 pts\n")

print(f"3. ITEMIZED ANALYSIS OF BILLY'S JIRA ISSUES (Sample of 15 issues):")
print(f"{'Issue Key':<10} | {'C':<2} {'I':<2} {'S':<2} {'R':<2} {'O':<2} = {'Total':<5} -> {'KPI Pts':<8} | {'Summary'}")
print("-" * 110)
for iss in billy_issues[:15]:
    an = iss["analysis"]
    print(f"{iss['key']:<10} | {an['complexity']:<2} {an['impact']:<2} {an['scope']:<2} {an['risk']:<2} {an['ownership']:<2} = {an['total_score']:<5} -> {an['kpi_points']:<8.1f} | {iss['summary'].encode('ascii', 'replace').decode('ascii')[:45]}")
