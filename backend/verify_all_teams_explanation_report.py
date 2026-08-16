import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from datetime import datetime
from feature_analyzer import calculate_feature_weight
from founder_engine import get_founder_credits_for_user, get_founder_projects_info

db = SessionLocal()

from_date = datetime(2026, 1, 1)
to_date = datetime(2026, 12, 31, 23, 59, 59)

def get_weight_reason(summary: str, weight: float) -> str:
    if weight == 110.0:
        return "Rebuild App Utama & Native OS Upgrade (e.g. 16KB ARM Page Size Compatibility)"
    elif weight == 25.0:
        return "Core Engine, DB Refactoring & Infrastructure Hardening"
    elif weight == 10.0:
        return "Fitur Utama Kerumitan Tinggi / Multi-Subtask Enhancement (>= 5 Subtasks)"
    elif weight == 7.0:
        return "Fitur Modul Menengah dengan Subtasks (2-4 Subtasks)"
    elif weight == 4.0:
        return "Fitur / Modul Standar Tunggal (Standard Module Implementation)"
    elif weight == 1.5:
        return "QA & Testing Verification (Verifikasi Pengujian QA/Tester)"
    elif weight == 1.0:
        return "Operasional Rutin / Support Staging / Upload Config / Change Banner"
    elif weight == 5.0:
        return "Fitur Tambahan Integrasi Modul"
    elif weight == 3.0:
        return "Perbaikan Minor / UI Styling Fix"
    else:
        return f"Evaluasi Bobot Fitur ({weight} Poin)"

users = db.query(models.User).filter(models.User.is_active == True).all()

report = []

for u in users:
    jira_ident = db.query(models.EmployeeIdentity).filter(
        models.EmployeeIdentity.user_id == u.id,
        models.EmployeeIdentity.source == 'jira'
    ).first()
    
    jira_account = jira_ident.external_user_id if jira_ident else None
    
    features = []
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
                        w = calculate_feature_weight(ji.raw_data or {})
                        tot_points += w
                        
                        fields = ji.raw_data.get('fields', {}) if ji.raw_data else {}
                        proj = fields.get('project', {}).get('name') or fields.get('project', {}).get('key', 'UNKNOWN')
                        summary = fields.get('summary', ji.issue_key)
                        clean_summary = summary.encode('ascii', 'replace').decode('ascii')
                        reason = get_weight_reason(summary, w)
                        
                        features.append({
                            "key": ji.issue_key,
                            "project": proj,
                            "summary": clean_summary,
                            "weight": w,
                            "reason": reason
                        })
                except Exception:
                    pass
                    
    founder_pts = get_founder_credits_for_user(u.id, target_year=2026)
    founder_projs = get_founder_projects_info(u.id, target_year=2026)
    
    report.append({
        "user_id": u.id,
        "name": u.full_name,
        "tot_points": tot_points,
        "features": features,
        "founder_pts": founder_pts,
        "founder_projs": founder_projs
    })

print("=== VERIFICATION OF TRANSPARENT FEATURE REASONING FOR ALL TEAMS ===")
for r in sorted(report, key=lambda x: (x["tot_points"] + x["founder_pts"]), reverse=True):
    print(f"\n==========================================================================================")
    print(f"KARYAWAN: {r['name']} (ID: {r['user_id']}) -> Total Poin Fitur: {r['tot_points']:.1f} Pts | Founder Pts: {r['founder_pts']:.1f} Pts")
    print(f"==========================================================================================")
    for i, f in enumerate(r['features'], start=1):
        print(f"   {i:<2}. [{f['key']}] ({f['weight']} Pts) {f['summary'][:40]:<41} | Alasan: {f['reason']}")
