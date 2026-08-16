import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from datetime import datetime

db = SessionLocal()

def auto_analyze_multi_factor(issue_data: dict) -> dict:
    """
    Automated Multi-Factor Scoring Engine for Jira Issues.
    Returns a dictionary of:
    - technical_complexity (0-5)
    - business_impact (0-5)
    - system_scope (0-5)
    - delivery_risk (0-3)
    - ownership_level (0-2)
    - total_score (0-20)
    - kpi_points (1-25)
    """
    fields = issue_data.get('fields', {}) if issue_data else {}
    summary = (fields.get('summary') or '').strip().lower()
    
    raw_desc = fields.get('description') or ''
    desc_text = ''
    if isinstance(raw_desc, str):
        desc_text = raw_desc.lower()
    elif isinstance(raw_desc, dict):
        desc_text = str(raw_desc).lower()
        
    combined_text = f"{summary} {desc_text}"
    
    # Extract structural metadata
    issuetype = (fields.get('issuetype') or {}).get('name', 'Task').lower()
    priority = (fields.get('priority') or {}).get('name', 'Medium').lower()
    subtasks = fields.get('subtasks', [])
    subtask_cnt = len(subtasks) if isinstance(subtasks, list) else 0
    story_points = float(issue_data.get('story_points') or 0.0)
    
    # 0. Check QA Task
    is_qa = summary.startswith('qa:') or 'qa test' in combined_text or 'test case' in combined_text or summary.startswith('testing')
    
    # 1. Technical Complexity (0-5)
    complexity = 2  # Default
    if is_qa:
        complexity = 2 if ('automation' in combined_text or 'regression' in combined_text or 'security' in combined_text) else 1
    elif any(kw in combined_text for kw in ['build ulang', 'rebuild', '16kb', '16 kb', 'arm compatibility']):
        complexity = 5
    elif any(kw in combined_text for kw in ['squash', 'refactor core', 'architecture overhaul', 'framework upgrade', 'zero-downtime', 'migration', 'blue-green']):
        complexity = 4
    elif 'epic' in issuetype:
        complexity = 5
    elif 'story' in issuetype:
        complexity = 3
    elif 'bug' in issuetype:
        complexity = 2
    elif 'sub-task' in issuetype or 'subtask' in issuetype:
        complexity = 1
        
    # Complexity adjustment based on scope
    if not is_qa:
        if subtask_cnt >= 8:
            complexity = max(complexity, 5)
        elif subtask_cnt >= 4:
            complexity = max(complexity, 4)
        elif story_points >= 8:
            complexity = min(complexity + 1, 5)
            
    # 2. Business Impact (0-5)
    impact = 2  # Default
    if any(kw in combined_text for kw in ['build ulang', 'rebuild', '16kb', '16 kb', 'arm compatibility', 'zero-downtime', 'blue-green deploy', 'security hardening', 'pentest']):
        impact = 5
    elif any(kw in combined_text for kw in ['doku', 'kredivo', 'payment', 'booking', 'overtime', 'roster', 'leave submission', 'quota management']):
        impact = 4
    elif any(kw in combined_text for kw in ['reporting', 'report', 'event support', 'travel fair', 'public event', 'private event']):
        impact = 3
    elif any(kw in combined_text for kw in ['theme option', 'styling', 'logo', 'aria-label']):
        impact = 2
    elif any(kw in combined_text for kw in ['upload gc', 'upload bca', 'banner', 'good morning', 'staging test', 'prod - test', 'username', 'password']):
        impact = 1
        
    # 3. System Scope (0-5)
    scope = 2  # Default
    if any(kw in combined_text for kw in ['16kb', '16 kb', 'arm compatibility', 'rebuild app', 'blue-green deploy', 'pentest remediation']):
        scope = 5
    elif any(kw in combined_text for kw in ['api integration', 'data sync', 'deployment', 'db setup']):
        scope = 4
    elif any(kw in combined_text for kw in ['doku', 'kredivo', 'payment gateway', 'prometheus', 'expiry check']):
        scope = 3
    elif any(kw in combined_text for kw in ['overtime order', 'leave request', 'roster alert', 'report generate']):
        scope = 2
    elif any(kw in combined_text for kw in ['banner', 'button', 'logo', 'good morning', 'username', 'password']):
        scope = 1

    # 4. Delivery Risk (0-3)
    risk = 1  # Default
    if any(kw in combined_text for kw in ['rebuild app', '16kb', 'zero-downtime', 'blue-green', 'pentest', 'prod deploy', 'security hardening']):
        risk = 3
    elif any(kw in combined_text for kw in ['overtime', 'leave submission', 'roster', 'api integration', 'data sync', 'payment gateway']):
        risk = 2
    elif is_qa or 'test' in summary or 'banner' in summary:
        risk = 1

    # 5. Ownership Level (0-2)
    ownership = 1  # Default (Primary Implementer)
    if is_qa:
        ownership = 0  # Contributor / Verification only
    elif any(kw in combined_text for kw in ['upload gc', 'banner', 'good morning', 'username', 'password', 'support']):
        ownership = 0  # Contributor
    elif any(kw in combined_text for kw in ['rebuild app', '16kb', 'zero-downtime', 'setup project & environment baru']) or subtask_cnt >= 5:
        ownership = 2  # Technical Owner
        
    # Calculate Total Score (max 20)
    total_score = complexity + impact + scope + risk + ownership
    total_score = min(total_score, 20)
    
    # Map to KPI Points
    # 18-20: 25 pts
    # 15-17: 20 pts
    # 12-14: 15 pts
    # 9-11: 10 pts
    # 6-8: 7 pts
    # 3-5: 4 pts
    # 1-2: 1 pt
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

# Test and run verification on 2026 team
from_date = datetime(2026, 1, 1)
to_date = datetime(2026, 12, 31, 23, 59, 59)
target_users = ['9615', '6592', '7052', '6518', '7690']

print("=== AUTOMATED MULTI-FACTOR ENGINE TEST FOR 2026 ===")
for uid in target_users:
    user = db.query(models.User).filter(models.User.id == uid).first()
    j_ident = db.query(models.EmployeeIdentity).filter(
        models.EmployeeIdentity.user_id == uid,
        models.EmployeeIdentity.source == 'jira'
    ).first()
    
    if not j_ident or not j_ident.external_user_id:
        continue
        
    jiras = db.query(models.RawJiraIssue).filter(
        models.RawJiraIssue.assignee_account_id == j_ident.external_user_id
    ).all()
    
    tot_points = 0.0
    tasks_cnt = 0
    print(f"\nUser: {user.full_name}")
    print(f"{'Key':<10} | {'Complexity':<10} | {'Impact':<7} | {'Scope':<6} | {'Risk':<5} | {'Owner':<6} | {'Total':<6} | {'Points':<7} | {'Summary'}")
    print("-" * 105)
    for ji in jiras[:8]:  # Show top 8 sample tasks
        r_date = ji.resolved_date or ji.updated_date or ji.created_date
        if r_date:
            try:
                r_dt = datetime.fromisoformat(str(r_date).replace('Z', '+00:00')) if isinstance(r_date, str) else r_date
                r_dt_naive = r_dt.replace(tzinfo=None) if hasattr(r_dt, 'replace') else r_dt
                if from_date <= r_dt_naive <= to_date:
                    tasks_cnt += 1
                    res = auto_analyze_multi_factor(ji.raw_data or {})
                    tot_points += res["kpi_points"]
                    print(f"{ji.issue_key:<10} | {res['complexity']:<10} | {res['impact']:<7} | {res['scope']:<6} | {res['risk']:<5} | {res['ownership']:<6} | {res['total_score']:<6} | {res['kpi_points']:<7} | {ji.raw_data.get('fields', {}).get('summary', ji.issue_key)[:30]}")
            except Exception:
                pass
