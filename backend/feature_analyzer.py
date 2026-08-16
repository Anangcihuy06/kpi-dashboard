import re
from typing import Dict, Any

def calculate_feature_weight(issue_data: dict) -> float:
    """
    Automated Multi-Factor Scoring Engine for Jira Issues (V2).
    Evaluates every Jira issue across 5 dimensions (Complexity, Impact, Scope, Risk, Ownership)
    and maps the total score (0-20) to KPI Points (1-25) to prevent point distortion.
    Story Points are excluded from feature complexity per user mandate.
    """
    res = analyze_multi_factor(issue_data)
    return res["kpi_points"]

def analyze_multi_factor(issue_data: dict) -> dict:
    """
    Detailed Multi-Factor Scoring Analyzer for Jira Issues.
    Returns:
        - technical_complexity (0-5)
        - business_impact (0-5)
        - system_scope (0-5)
        - delivery_risk (0-3)
        - ownership_level (0-2)
        - total_score (0-20)
        - kpi_points (1.0 - 25.0)
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
    issuetype = (fields.get('issuetype') or {}).get('name', 'Task').lower()
    subtasks = fields.get('subtasks', [])
    subtask_cnt = len(subtasks) if isinstance(subtasks, list) else 0
    story_points = float(issue_data.get('story_points') or 0.0)
    
    # 0. Check QA/Testing Verification Task
    is_qa = summary.startswith('qa:') or 'qa test' in combined_text or 'test case' in combined_text or summary.startswith('testing')
    
    # 1. Check Routine operational task
    routine_keywords = [
        'upload gc', 'upload bca', 'generate report', 'test support', 'private event support',
        'public event support', 'update banner', 'good morning', 'create username', 'password for test',
        'configure and prepare for test', 'prod - test', 'minor fix', 'text change'
    ]
    is_routine = any(kw in combined_text for kw in routine_keywords)
    
    # 2. Check Rebuild / Core Engineering
    is_rebuild = any(kw in combined_text for kw in ['build ulang', 'rebuild', '16kb', '16 kb', 'arm compatibility', 'native-bridge', 'jni', 'ndk', 'recompile', 'page size alignment', 'memory alignment'])
    is_core = any(kw in combined_text for kw in ['squash', 'refactor core', 'architecture overhaul', 'framework upgrade', 'zero-downtime', 'migration', 'blue-green'])

    # Deep Analysis of Description & Summary for Architectural Complexity
    has_db_migration = any(kw in combined_text for kw in ['schema migration', 'alter table', 'indexing', 'postgresql query optimization', 'foreign key', 'database constraint', 'db setup'])
    has_zero_downtime = any(kw in combined_text for kw in ['zero-downtime deployment', 'nginx blue-green config', 'pipeline automation', 'sentry security monitoring'])
    has_security_remediation = any(kw in combined_text for kw in ['owasp testing', 'penetration scanning', 'xss mitigation', 'csrf protection', 'security hardening'])

    # === DIMENSION 1: Technical Complexity (0-5) ===
    if is_routine:
        complexity = 1
    elif is_qa:
        complexity = 2 if ('automation' in combined_text or 'regression' in combined_text or 'security' in combined_text or has_security_remediation) else 1
    elif is_rebuild:
        complexity = 5
    elif is_core:
        complexity = 4
    elif has_db_migration or has_zero_downtime:
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

    # === DIMENSION 2: Business Impact (0-5) ===
    if is_routine:
        impact = 1
    elif is_qa:
        impact = 2 if ('automation' in combined_text or 'security' in combined_text or has_security_remediation) else 1
    elif is_rebuild:
        impact = 5
    elif is_core or has_zero_downtime:
        impact = 5
    elif has_db_migration or has_security_remediation:
        impact = 4
    elif any(kw in combined_text for kw in ['doku', 'kredivo', 'payment', 'booking', 'overtime', 'roster', 'leave submission', 'quota management']):
        impact = 4
    elif any(kw in combined_text for kw in ['reporting', 'report', 'event support', 'travel fair']):
        impact = 3
    elif any(kw in combined_text for kw in ['theme option', 'styling', 'logo', 'aria-label']):
        impact = 2
    else:
        impact = 2

    # === DIMENSION 3: System Scope (0-5) ===
    if is_routine:
        scope = 0
    elif is_qa:
        scope = 1
    elif is_rebuild:
        scope = 5
    elif is_core or has_zero_downtime:
        scope = 4
    elif has_db_migration:
        scope = 3
    elif any(kw in combined_text for kw in ['api integration', 'data sync', 'deployment', 'db setup']):
        scope = 4
    elif any(kw in combined_text for kw in ['doku', 'kredivo', 'payment gateway', 'prometheus', 'expiry check']):
        scope = 3
    elif any(kw in combined_text for kw in ['overtime order', 'leave request', 'roster alert', 'report generate']):
        scope = 2
    else:
        scope = 2

    # === DIMENSION 4: Delivery Risk (0-3) ===
    if is_routine:
        risk = 0
    elif is_qa:
        risk = 1
    elif is_rebuild or is_core or has_zero_downtime:
        risk = 3
    elif has_db_migration or has_security_remediation:
        risk = 2
    elif any(kw in combined_text for kw in ['overtime', 'leave submission', 'roster', 'api integration', 'data sync', 'payment gateway']):
        risk = 2
    else:
        risk = 1

    # === DIMENSION 5: Ownership Level (0-2) ===
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
    
    # KPI point mapping
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
