import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from datetime import datetime
from feature_analyzer import calculate_feature_weight
from founder_engine import get_founder_credits_for_user

db = SessionLocal()

def calculate_pure_feature_matrix(year: int):
    from_date = datetime(year, 1, 1)
    to_date = datetime(year, 12, 31, 23, 59, 59)
    
    users = db.query(models.User).filter(models.User.is_active == True).all()
    
    user_metrics = {}
    
    for u in users:
        # 1. Feature & Module Architectural Complexity Weight (Pure Feature Analysis)
        jira_ident = db.query(models.EmployeeIdentity).filter(
            models.EmployeeIdentity.user_id == u.id,
            models.EmployeeIdentity.source == 'jira'
        ).first()
        
        complexity_pts = 0.0
        tasks_cnt = 0
        
        if jira_ident and jira_ident.external_user_id:
            raw_jiras = db.query(models.RawJiraIssue).filter(
                models.RawJiraIssue.assignee_account_id == jira_ident.external_user_id
            ).all()
            
            for ji in raw_jiras:
                r_date = ji.resolved_date or ji.updated_date or ji.created_date
                if r_date:
                    try:
                        r_dt = datetime.fromisoformat(str(r_date).replace('Z', '+00:00')) if isinstance(r_date, str) else r_date
                        r_dt_naive = r_dt.replace(tzinfo=None) if hasattr(r_dt, 'replace') else r_dt
                        if from_date <= r_dt_naive <= to_date:
                            tasks_cnt += 1
                            # Feature analysis evaluating task title, subtasks, rebuild keywords, architecture scope
                            feat_w = calculate_feature_weight(ji.raw_data or {})
                            complexity_pts += float(feat_w)
                    except Exception:
                        pass
                        
        # 2. Founder Project Credit for target year
        founder_pts = get_founder_credits_for_user(u.id, target_year=year)
        
        # 3. Attendance Days & Late Count
        daily_records = db.query(models.KPIEmployeeDaily).filter(
            models.KPIEmployeeDaily.user_id == u.id,
            models.KPIEmployeeDaily.date >= from_date,
            models.KPIEmployeeDaily.date <= to_date
        ).all()
        
        att_days = sum(d.attendance_days for d in daily_records)
        late_cnt = sum(d.late_count for d in daily_records)
        
        user_metrics[u.id] = {
            "name": u.full_name,
            "complexity_pts": complexity_pts,
            "tasks_cnt": tasks_cnt,
            "founder_pts": founder_pts,
            "att_days": att_days,
            "late_cnt": late_cnt
        }
        
    # Find team maxima for relative benchmarks
    max_complexity = max(m["complexity_pts"] for m in user_metrics.values()) or 1.0
    max_tasks = max(m["tasks_cnt"] for m in user_metrics.values()) or 1.0
    max_founder = max(m["founder_pts"] for m in user_metrics.values()) or 1.0
    
    print(f"\n=========================================================================")
    print(f"=== PURE FEATURE & ARCHITECTURE WEIGHT KPI MATRIX FOR YEAR {year} ===")
    print(f"=== (STORY POINTS COMPLETELY EXCLUDED - 100% OBJECTIVE FEATURE WEIGHT) ===")
    print(f"Team Maxima -> Feature Complexity: {max_complexity} pts | Max Tasks: {max_tasks} | Founder Pts: {max_founder}")
    print(f"=========================================================================")
    
    for uid, m in sorted(user_metrics.items(), key=lambda x: x[1]['name']):
        # Pillar 1: Feature & Module Architectural Weight (40%)
        s1 = min((m["complexity_pts"] / max_complexity) * 100, 100.0) if max_complexity > 0 else 0.0
        w1 = s1 * 0.40
        
        # Pillar 2: Task & Feature Delivery Velocity (30%)
        s2 = min((m["tasks_cnt"] / max_tasks) * 100, 100.0) if max_tasks > 0 else 0.0
        w2 = s2 * 0.30
        
        # Pillar 3: Project Founder Architecture Credit (20%)
        s3 = min((m["founder_pts"] / max_founder) * 100, 100.0) if max_founder > 0 else 0.0
        w3 = s3 * 0.20
        
        # Pillar 4: Attendance & Punctuality (10%)
        target_days = 261.0
        late_pct = (m["late_cnt"] / target_days * 100) if target_days > 0 else 0.0
        s4 = max((m["att_days"] / target_days) * 100 - (late_pct * 0.5), 0.0)
        w4 = s4 * 0.10
        
        total_kpi = w1 + w2 + w3 + w4
        
        print(f"\nUser {uid} ({m['name']}) -> FINAL OVERALL KPI: {round(total_kpi, 2)} / 100")
        print(f"   1. Feature Complexity Weight (40%): Raw = {m['complexity_pts']} pts | Score = {round(s1, 1)}% | Weighted = {round(w1, 2)}")
        print(f"   2. Task & Module Delivery (30%): Raw = {m['tasks_cnt']} Tasks | Score = {round(s2, 1)}% | Weighted = {round(w2, 2)}")
        print(f"   3. Project Founder Credit (20%): Raw = {m['founder_pts']} pts | Score = {round(s3, 1)}% | Weighted = {round(w3, 2)}")
        print(f"   4. Attendance Discipline (10%): Raw = {m['att_days']} Days ({m['late_cnt']} Late) | Score = {round(s4, 1)}% | Weighted = {round(w4, 2)}")

calculate_pure_feature_matrix(2026)
