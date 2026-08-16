import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from datetime import datetime
from feature_analyzer import calculate_feature_weight
from founder_engine import get_founder_credits_for_user

db = SessionLocal()

def calculate_5pillar_matrix(year: int):
    from_date = datetime(year, 1, 1)
    to_date = datetime(year, 12, 31, 23, 59, 59)
    
    users = db.query(models.User).filter(models.User.is_active == True).all()
    
    user_metrics = {}
    
    for u in users:
        # 1. Raw Jira SP & Complexity SP
        jira_ident = db.query(models.EmployeeIdentity).filter(
            models.EmployeeIdentity.user_id == u.id,
            models.EmployeeIdentity.source == 'jira'
        ).first()
        
        raw_sp = 0.0
        complexity_sp = 0.0
        issues_cnt = 0
        
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
                            issues_cnt += 1
                            sp = float(ji.story_points or 0.0)
                            cw = calculate_feature_weight(ji.raw_data or {})
                            raw_sp += sp
                            complexity_sp += (sp + cw)
                    except Exception:
                        pass
                        
        # 2. Founder Credit for target year
        founder_sp = get_founder_credits_for_user(u.id, target_year=year)
        
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
            "raw_sp": raw_sp,
            "complexity_sp": complexity_sp,
            "issues_cnt": issues_cnt,
            "founder_sp": founder_sp,
            "att_days": att_days,
            "late_cnt": late_cnt
        }
        
    # Find team maxima for relative benchmarks
    max_raw_sp = max(m["raw_sp"] for m in user_metrics.values()) or 1.0
    max_complexity_sp = max(m["complexity_sp"] for m in user_metrics.values()) or 1.0
    max_founder_sp = max(m["founder_sp"] for m in user_metrics.values()) or 1.0
    max_issues_cnt = max(m["issues_cnt"] for m in user_metrics.values()) or 1.0
    
    print(f"\n=======================================================")
    print(f"=== 5-PILLAR ARCHITECTURAL KPI MATRIX FOR YEAR {year} ===")
    print(f"Team Maxima -> Raw SP: {max_raw_sp} | Complexity SP: {max_complexity_sp} | Founder SP: {max_founder_sp} | Max Issues: {max_issues_cnt}")
    print(f"=======================================================")
    
    for uid, m in user_metrics.items():
        # Pillar 1: Jira SP Volume (30%)
        s1 = min((m["raw_sp"] / max_raw_sp) * 100, 100.0)
        w1 = s1 * 0.30
        
        # Pillar 2: Feature Complexity & Difficulty (25%)
        s2 = min((m["complexity_sp"] / max_complexity_sp) * 100, 100.0)
        w2 = s2 * 0.25
        
        # Pillar 3: Sprint Delivery Speed & Execution (20%)
        s3 = min((m["issues_cnt"] / max_issues_cnt) * 100, 100.0)
        w3 = s3 * 0.20
        
        # Pillar 4: Project Founder Credit (15%)
        s4 = min((m["founder_sp"] / max_founder_sp) * 100, 100.0) if max_founder_sp > 0 else 0.0
        w4 = s4 * 0.15
        
        # Pillar 5: Attendance & Punctuality (10%)
        target_days = 261.0
        late_pct = (m["late_cnt"] / target_days * 100) if target_days > 0 else 0.0
        s5 = max((m["att_days"] / target_days) * 100 - (late_pct * 0.5), 0.0)
        w5 = s5 * 0.10
        
        total_kpi = w1 + w2 + w3 + w4 + w5
        
        print(f"\nUser {uid} ({m['name']}) -> OVERALL KPI: {round(total_kpi, 2)} / 100")
        print(f"   1. Jira SP Volume (30%): Raw = {m['raw_sp']} SP | Score = {round(s1, 1)}% | Weighted = {round(w1, 2)}")
        print(f"   2. Feature Complexity (25%): Raw = {m['complexity_sp']} SP | Score = {round(s2, 1)}% | Weighted = {round(w2, 2)}")
        print(f"   3. Sprint Delivery (20%): Raw = {m['issues_cnt']} Issues | Score = {round(s3, 1)}% | Weighted = {round(w3, 2)}")
        print(f"   4. Project Founder (15%): Raw = {m['founder_sp']} SP | Score = {round(s4, 1)}% | Weighted = {round(w4, 2)}")
        print(f"   5. Attendance (10%): Raw = {m['att_days']} Days ({m['late_cnt']} Late) | Score = {round(s5, 1)}% | Weighted = {round(w5, 2)}")

calculate_5pillar_matrix(2026)
