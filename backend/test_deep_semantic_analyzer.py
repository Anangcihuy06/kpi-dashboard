import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from datetime import datetime

db = SessionLocal()

def deep_semantic_feature_weight(issue_data: dict) -> float:
    fields = issue_data.get('fields', {}) if issue_data else {}
    summary = (fields.get('summary') or '').lower()
    
    raw_desc = fields.get('description') or ''
    desc_text = ''
    if isinstance(raw_desc, str):
        desc_text = raw_desc.lower()
    elif isinstance(raw_desc, dict):
        desc_text = str(raw_desc).lower()
        
    combined_text = f"{summary} {desc_text}"
    
    # 1. ROUTINE / TRIVIAL MAINTENANCE DEMOTION (Mengolah Makna Isi Tiket Routine)
    routine_keywords = [
        'upload gc', 'upload bca', 'generate report', 'test support', 'private event support',
        'public event support', 'update banner', 'good morning', 'create username', 'password for test',
        'configure and prepare for test', 'prod - test', 'minor fix', 'text change'
    ]
    
    is_routine = any(kw in combined_text for kw in routine_keywords)
    
    # 2. DEEP ARCHITECTURAL & CORE REBUILD HEAVY IMPACT
    rebuild_keywords = [
        'build ulang', 'rebuild app', 'rebuild application', 'rebuild mobile', 'rebuild web', 
        '16 kb', '16kb', 'overhaul app', 'app baru', 'arm compatibility', '16kb arm'
    ]
    is_rebuild = any(kw in combined_text for kw in rebuild_keywords)
    
    core_engineering_keywords = [
        'squash 62 ad-hoc db migrations', 'zero-downtime blue-green deploy', 'post-pentest',
        'security hardening', 'refactor core', 'architecture overhaul', 'framework upgrade',
        'core module', 'api integration & data sync', 'setup project & environment baru'
    ]
    is_core = any(kw in combined_text for kw in core_engineering_keywords)
    
    # Subtasks count
    subtasks = fields.get('subtasks', [])
    subtask_cnt = len(subtasks) if isinstance(subtasks, list) else 0
    
    # Calculate Semantic Weight
    if is_rebuild:
        weight = 110.0  # Massive App Rebuild (e.g. F20M-27 16KB ARM)
    elif is_core:
        weight = 25.0   # Core Engineering / Security / DB Refactoring
    elif is_routine:
        weight = 1.0    # Trivial Operational / Maintenance task
    else:
        # Standard Feature
        if subtask_cnt >= 5:
            weight = 10.0
        elif subtask_cnt >= 2:
            weight = 7.0
        else:
            weight = 4.0
            
    return weight

from_date = datetime(2026, 1, 1)
to_date = datetime(2026, 12, 31, 23, 59, 59)
target_users = ['9615', '6592', '7052', '6518', '7690']

print("=== DEEP SEMANTIC ANALYZER TEST FOR YEAR 2026 ===")

for uid in target_users:
    user = db.query(models.User).filter(models.User.id == uid).first()
    jira_ident = db.query(models.EmployeeIdentity).filter(
        models.EmployeeIdentity.user_id == uid,
        models.EmployeeIdentity.source == 'jira'
    ).first()
    
    if not jira_ident or not jira_ident.external_user_id:
        continue
        
    jiras = db.query(models.RawJiraIssue).filter(
        models.RawJiraIssue.assignee_account_id == jira_ident.external_user_id
    ).all()
    
    tot_semantic_weight = 0.0
    tasks_cnt = 0
    routine_cnt = 0
    core_cnt = 0
    
    for ji in jiras:
        r_date = ji.resolved_date or ji.updated_date or ji.created_date
        if r_date:
            try:
                r_dt = datetime.fromisoformat(str(r_date).replace('Z', '+00:00')) if isinstance(r_date, str) else r_date
                r_dt_naive = r_dt.replace(tzinfo=None) if hasattr(r_dt, 'replace') else r_dt
                if from_date <= r_dt_naive <= to_date:
                    tasks_cnt += 1
                    sw = deep_semantic_feature_weight(ji.raw_data or {})
                    tot_semantic_weight += sw
                    if sw == 1.0:
                        routine_cnt += 1
                    elif sw >= 25.0:
                        core_cnt += 1
            except Exception:
                pass
                
    print(f"\nUser {uid} ({user.full_name}):")
    print(f"   - Total Tasks: {tasks_cnt} (Core/Rebuild Tasks: {core_cnt}, Routine/Maintenance Tasks: {routine_cnt})")
    print(f"   - Deep Semantic Architectural Weight: {tot_semantic_weight} pts")
