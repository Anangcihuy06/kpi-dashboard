import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from datetime import datetime
from founder_engine import get_founder_credits_for_user, get_founder_projects_info

db = SessionLocal()

def auto_analyze_multi_factor(issue_data: dict) -> dict:
    fields = issue_data.get('fields', {}) if issue_data else {}
    summary = (fields.get('summary') or '').strip().lower()
    
    raw_desc = fields.get('description') or ''
    desc_text = ''
    if isinstance(raw_desc, str):
        desc_text = raw_desc.lower()
    elif isinstance(raw_desc, dict):
        desc_text = str(raw_desc).lower()
        
    combined_text = f"{summary} {desc_text}"
    issuetype = (fields.get('issuetype') or {}).get('name', 'Task').lower()
    subtasks = fields.get('subtasks', [])
    subtask_cnt = len(subtasks) if isinstance(subtasks, list) else 0
    story_points = float(issue_data.get('story_points') or 0.0)
    
    # 0. Check QA Task
    is_qa = summary.startswith('qa:') or 'qa test' in combined_text or 'test case' in combined_text or summary.startswith('testing')
    
    # 1. Check Routine task
    routine_keywords = [
        'upload gc', 'upload bca', 'generate report', 'test support', 'private event support',
        'public event support', 'update banner', 'good morning', 'create username', 'password for test',
        'configure and prepare for test', 'prod - test', 'minor fix', 'text change'
    ]
    is_routine = any(kw in combined_text for kw in routine_keywords)
    
    # 2. Check Rebuild / Core Engineering
    is_rebuild = any(kw in combined_text for kw in ['build ulang', 'rebuild', '16kb', '16 kb', 'arm compatibility'])
    is_core = any(kw in combined_text for kw in ['squash', 'refactor core', 'architecture overhaul', 'framework upgrade', 'zero-downtime', 'migration', 'blue-green'])

    # Determine Complexity (0-5)
    if is_routine:
        complexity = 1
    elif is_qa:
        complexity = 2 if ('automation' in combined_text or 'regression' in combined_text or 'security' in combined_text) else 1
    elif is_rebuild:
        complexity = 5
    elif is_core:
        complexity = 4
    elif 'epic' in issuetype:
        complexity = 5
    elif 'story' in issuetype:
        complexity = 3
    elif 'bug' in issuetype:
        complexity = 2
    else:
        complexity = 2
        
    if not is_qa and not is_routine:
        if subtask_cnt >= 8:
            complexity = max(complexity, 5)
        elif subtask_cnt >= 4:
            complexity = max(complexity, 4)
        elif story_points >= 8:
            complexity = min(complexity + 1, 5)

    # Determine Business Impact (0-5)
    if is_routine:
        impact = 1
    elif is_qa:
        impact = 2 if ('automation' in combined_text or 'security' in combined_text) else 1
    elif is_rebuild:
        impact = 5
    elif is_core:
        impact = 4
    elif any(kw in combined_text for kw in ['doku', 'kredivo', 'payment', 'booking', 'overtime', 'roster', 'leave submission', 'quota management']):
        impact = 4
    elif any(kw in combined_text for kw in ['reporting', 'report', 'event support', 'travel fair']):
        impact = 3
    elif any(kw in combined_text for kw in ['theme option', 'styling', 'logo', 'aria-label']):
        impact = 2
    else:
        impact = 2

    # Determine System Scope (0-5)
    if is_routine:
        scope = 0
    elif is_qa:
        scope = 1
    elif is_rebuild:
        scope = 5
    elif is_core:
        scope = 4
    elif any(kw in combined_text for kw in ['api integration', 'data sync', 'deployment', 'db setup']):
        scope = 4
    elif any(kw in combined_text for kw in ['doku', 'kredivo', 'payment gateway', 'prometheus', 'expiry check']):
        scope = 3
    elif any(kw in combined_text for kw in ['overtime order', 'leave request', 'roster alert', 'report generate']):
        scope = 2
    else:
        scope = 2

    # Determine Delivery Risk (0-3)
    if is_routine:
        risk = 0
    elif is_qa:
        risk = 1
    elif is_rebuild or is_core:
        risk = 3
    elif any(kw in combined_text for kw in ['overtime', 'leave submission', 'roster', 'api integration', 'data sync', 'payment gateway']):
        risk = 2
    else:
        risk = 1

    # Determine Ownership Level (0-2)
    if is_qa or is_routine:
        ownership = 0
    elif is_rebuild:
        ownership = 2
    elif subtask_cnt >= 5 or story_points >= 8:
        ownership = 2
    else:
        ownership = 1

    total_score = complexity + impact + scope + risk + ownership
    total_score = min(total_score, 20)
    
    if total_score >= 18:
        kpi_points = 25.0
    elif total_score >= 15:
        kpi_points = 20.0
    elif total_score >= 12:
        kpi_points = 15.0
    elif total_score >= 9:
        kpi_points = 10.0
    elif total_score >= 6:
        kpi_points = 7.0
    elif total_score >= 3:
        kpi_points = 4.0
    else:
        kpi_points = 1.0
        
    return {
        "complexity": complexity,
        "impact": impact,
        "scope": scope,
        "risk": risk,
        "ownership": ownership,
        "total_score": total_score,
        "kpi_points": kpi_points
    }

from_date = datetime(2026, 1, 1)
to_date = datetime(2026, 12, 31, 23, 59, 59)
users = db.query(models.User).filter(models.User.is_active == True).all()

report_data = []

for u in users:
    j_ident = db.query(models.EmployeeIdentity).filter(
        models.EmployeeIdentity.user_id == u.id,
        models.EmployeeIdentity.source == 'jira'
    ).first()
    
    jira_account = j_ident.external_user_id if j_ident else None
    
    features_built = []
    tot_points = 0.0
    
    if jira_account:
        jiras = db.query(models.RawJiraIssue).filter(
            models.RawJiraIssue.assignee_account_id == jira_account
        ).all()
        
        for ji in jiras:
            r_date = ji.resolved_date or ji.updated_date or ji.created_date
            if r_date:
                try:
                    r_dt = datetime.fromisoformat(str(r_date).replace('Z', '+00:00')) if isinstance(r_date, str) else r_date
                    r_dt_naive = r_dt.replace(tzinfo=None) if hasattr(r_dt, 'replace') else r_dt
                    if from_date <= r_dt_naive <= to_date:
                        res = auto_analyze_multi_factor(ji.raw_data or {})
                        tot_points += res["kpi_points"]
                        features_built.append({
                            "key": ji.issue_key,
                            "points": res["kpi_points"],
                            "summary": ji.raw_data.get('fields', {}).get('summary', ji.issue_key).encode('ascii', 'replace').decode('ascii')
                        })
                except Exception:
                    pass
                    
    # Founder Credit 2026
    founder_pts = get_founder_credits_for_user(u.id, target_year=2026)
    founder_projs = get_founder_projects_info(u.id, target_year=2026)
    
    # Attendance 2026
    daily_recs = db.query(models.KPIEmployeeDaily).filter(
        models.KPIEmployeeDaily.user_id == u.id,
        models.KPIEmployeeDaily.date >= from_date,
        models.KPIEmployeeDaily.date <= to_date
    ).all()
    
    att_days = sum(d.attendance_days for d in daily_recs)
    late_cnt = sum(d.late_count for d in daily_recs)
    late_pct = (late_cnt / 261.0 * 100) if 261.0 > 0 else 0
    att_score = max((att_days / 261.0) * 100 - (late_pct * 0.5), 0.0)
    
    report_data.append({
        "user_id": u.id,
        "name": u.full_name,
        "tot_points": tot_points,
        "features_built": features_built,
        "founder_points": founder_pts,
        "founder_projects": founder_projs,
        "attendance_days": att_days,
        "late_count": late_cnt,
        "attendance_score": att_score
    })

# Benchmarks
max_feat_pts = max(r["tot_points"] for r in report_data) or 1.0
max_tasks_cnt = max(len(r["features_built"]) for r in report_data) or 1
max_founder_pts = max(r["founder_points"] for r in report_data) or 1.0

print("=== FINAL RE-CALIBRATED MULTI-FACTOR LEADERBOARD (YEAR 2026) ===")
for r in sorted(report_data, key=lambda x: (x["tot_points"] + x["founder_points"]), reverse=True):
    # Normalized weights
    feat_score = (r["tot_points"] / max_feat_pts) * 100
    w_feat = feat_score * 0.40
    
    tasks_cnt = len(r["features_built"])
    task_score = (tasks_cnt / max_tasks_cnt) * 100
    w_task = task_score * 0.30
    
    fnd_score = (r["founder_points"] / max_founder_pts) * 100 if max_founder_pts > 0 else 0.0
    w_fnd = fnd_score * 0.20
    
    w_att = r["attendance_score"] * 0.10
    
    final_score = w_feat + w_task + w_fnd + w_att
    
    print(f"User: {r['name']:<30} | Feat Pts: {r['tot_points']:<6.1f} | Tasks: {tasks_cnt:<3} | Founder Pts: {r['founder_points']:<6.1f} | Att: {r['attendance_score']:<5.1f}% | Final Score: {final_score:.2f}")
