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

users = db.query(models.User).filter(models.User.is_active == True).all()

report_data = []

for u in users:
    jira_ident = db.query(models.EmployeeIdentity).filter(
        models.EmployeeIdentity.user_id == u.id,
        models.EmployeeIdentity.source == 'jira'
    ).first()
    
    jira_account = jira_ident.external_user_id if jira_ident else None
    
    features_built = []
    tot_feat_points = 0.0
    
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
                        tot_feat_points += w
                        
                        fields = ji.raw_data.get('fields', {}) if ji.raw_data else {}
                        proj = fields.get('project', {}).get('name') or fields.get('project', {}).get('key', 'UNKNOWN')
                        summary = fields.get('summary', ji.issue_key)
                        # Sanitize non-ascii chars for print safety
                        clean_summary = summary.encode('ascii', 'replace').decode('ascii')
                        
                        features_built.append({
                            "key": ji.issue_key,
                            "project": proj,
                            "summary": clean_summary,
                            "weight": w
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
        "features_built": features_built,
        "total_feature_points": tot_feat_points,
        "founder_points": founder_pts,
        "founder_projects": founder_projs,
        "attendance_days": att_days,
        "late_count": late_cnt,
        "attendance_score": att_score
    })

# Compute relative benchmarks for transparency
max_feat_pts = max(r["total_feature_points"] for r in report_data) or 1.0
max_founder_pts = max(r["founder_points"] for r in report_data) or 1.0
max_tasks_cnt = max(len(r["features_built"]) for r in report_data) or 1

print(f"=== ITEMIZED TRANSPARENT FEATURE & ARCHITECTURE KPI REPORT FOR YEAR 2026 ===")

for r in sorted(report_data, key=lambda x: (x["total_feature_points"] + x["founder_points"]), reverse=True):
    feat_score = (r["total_feature_points"] / max_feat_pts) * 100
    w_feat = feat_score * 0.40
    
    tasks_cnt = len(r["features_built"])
    task_score = (tasks_cnt / max_tasks_cnt) * 100
    w_task = task_score * 0.30
    
    fnd_score = (r["founder_points"] / max_founder_pts) * 100 if max_founder_pts > 0 else 0.0
    w_fnd = fnd_score * 0.20
    
    w_att = r["attendance_score"] * 0.10
    
    final_score = w_feat + w_task + w_fnd + w_att
    
    print(f"\n==========================================================================================")
    print(f"KARYAWAN: {r['name']} (ID: {r['user_id']})")
    print(f"   - TOTAL AKUMULASI POIN FITUR (2026) : {r['total_feature_points']:.1f} Poin (dari {tasks_cnt} Fitur/Task)")
    print(f"   - KREDIT ABADI FOUNDER PROJECT (2026): {r['founder_points']:.1f} Poin ({len(r['founder_projects'])} Repo Lahir 2026)")
    print(f"   - SKOR PRESENSI ATTENDANCE           : {r['attendance_days']} Hari ({r['late_count']} Late) -> {r['attendance_score']:.2f}%")
    print(f"   - OVERALL KPI SCORE 2026             : {final_score:.2f} / 100")
    print(f"==========================================================================================")
    
    if r['features_built']:
        print(f"   [RINCIAN FITUR YANG DIBUAT TAHUN 2026 ({len(r['features_built'])} Task)]:")
        print(f"   {'No':<3} | {'Issue Key':<10} | {'Project Name':<24} | {'Bobot Poin':<10} | {'Nama Fitur / Module':<45}")
        print(f"   " + "-" * 98)
        for i, f in enumerate(r['features_built'], start=1):
            print(f"   {i:<3} | {f['key']:<10} | {f['project']:<24} | {f['weight']:<10.1f} | {f['summary'][:44]:<45}")
    else:
        print("   [RINCIAN FITUR]: Tidak ada data fitur/task Jira yang diselesaikan di tahun 2026.")
        
    if r['founder_projects']:
        print(f"\n   [KREDIT ABADI FOUNDER PROJECT ({len(r['founder_projects'])} Repo Lahir 2026)]:")
        for fp in r['founder_projects']:
            print(f"      + {fp['project_key']} (+150.0 Poin Inception Credit)")
