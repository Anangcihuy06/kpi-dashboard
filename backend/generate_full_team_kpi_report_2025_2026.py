import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from datetime import datetime
import json
import requests

db = SessionLocal()

def get_year_report(year: int):
    url = f"http://localhost:8000/api/v1/kpi/team-yearly?user_id=482&year={year}"
    r = requests.get(url)
    if r.status_code != 200:
        print(f"Error fetching data for year {year}: {r.status_code}")
        return []
    return r.json().get('data', [])

print(f"=== GENERATING FULL SUBORDINATES KPI REPORT FOR 2025 & 2026 ===")

for yr in [2025, 2026]:
    members = get_year_report(yr)
    print(f"\n==========================================================================================")
    print(f"=== LAPORAN MATRIKS KPI MURNI ANALISIS FITUR & ARSITEKTUR TAHUN {yr} ({len(members)} KARYAWAN) ===")
    print(f"==========================================================================================")
    
    members_sorted = sorted(members, key=lambda x: x.get('kpi_scores', {}).get('overall', 0), reverse=True)
    
    for idx, m in enumerate(members_sorted, start=1):
        uname = m.get('full_name')
        uid = m.get('user_id')
        role = m.get('role', 'Developer')
        scores = m.get('kpi_scores', {})
        overall = scores.get('overall', 0.0)
        details = scores.get('details', [])
        summary = m.get('summary', {})
        
        print(f"\n#{idx} {uname} (ID: {uid} | Role: {role}) -> FINAL OVERALL KPI SCORE: {overall:.2f} / 100")
        print(f"   --------------------------------------------------------------------------------------")
        print(f"   | Indikator Pillar                | Nilai Raw            | Benchmark  | Capped % | Bobot | Score  |")
        print(f"   --------------------------------------------------------------------------------------")
        
        for d in details:
            mkey = d.get('metric_key')
            lbl = d.get('label', mkey)
            raw = d.get('actual_value')
            c_score = d.get('calculated_score', 0.0)
            weight = d.get('weight', 0.0) * 100
            w_score = d.get('weighted_score', 0.0)
            vars_dict = d.get('variables', {})
            
            bench = list(vars_dict.values())[0] if vars_dict else "-"
            
            print(f"   | {lbl:<31} | {str(raw):<20} | {str(bench):<10} | {c_score:>7.2f}% | {weight:>4.0f}% | {w_score:>6.2f} |")
        print(f"   --------------------------------------------------------------------------------------")
        
        founder_projs = summary.get('founder_projects', [])
        if founder_projs:
            p_names = [p.get('project_key') for p in founder_projs]
            print(f"   [FOUNDER CREDIT ({len(p_names)} Repo Lahir {yr})]: {', '.join(p_names)}")

