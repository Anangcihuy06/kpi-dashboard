import json

with open('c:/Users/ATI-User/KPI-Dashboard/backend/autodetected_founders.json', 'r', encoding='utf-8') as f:
    founders = json.load(f)

by_user = {}
for f in founders:
    name = f.get('founder_name')
    uid = f.get('founder_user_id')
    pname = f.get('project_name')
    date = (f.get('initial_commit_date') or '')[:10]
    
    key = (uid, name)
    if key not in by_user:
        by_user[key] = []
    by_user[key].append({"project_name": pname, "date": date})

with open('c:/Users/ATI-User/KPI-Dashboard/backend/founder_projects_report.txt', 'w', encoding='utf-8') as out:
    out.write("=== DETAILED FOUNDER PROJECTS LIST PER EMPLOYEE ===\n")
    for (uid, name), projs in sorted(by_user.items(), key=lambda x: len(x[1]), reverse=True):
        out.write(f"\nKaryawan: {name} (ID {uid}) - Total {len(projs)} Projects (+{len(projs)*150} SP Founder Credit)\n")
        for idx, p in enumerate(projs, 1):
            out.write(f"   {idx}. {p['project_name']} (Inception Date: {p['date']})\n")

print("Report saved to founder_projects_report.txt!")
