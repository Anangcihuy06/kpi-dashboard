import requests
import json

def get_detailed_year_report(year: int):
    r = requests.get(f'http://localhost:8000/api/v1/kpi/team-yearly?user_id=482&year={year}')
    if r.status_code != 200:
        return []
    
    data = r.json().get('data', [])
    report = []
    
    # Determine top performer SP in the response
    max_sp = 0.0
    for u in data:
        sp = u.get('summary', {}).get('total_story_points', 0.0)
        if sp > max_sp:
            max_sp = sp
            
    for u in data:
        uid = u.get('user_id')
        name = u.get('full_name')
        summary = u.get('summary', {})
        scores = u.get('kpi_scores', {})
        
        tot_sp = summary.get('total_story_points', 0.0)
        founder_credit = summary.get('founder_architecture_credit', 0.0)
        founder_projs = summary.get('founder_projects', [])
        founder_count = len(founder_projs)
        
        att_days = summary.get('total_attendance_days', 0)
        late_cnt = summary.get('total_late_count', 0)
        jira_issues = summary.get('total_issues_completed', 0)
        commits = summary.get('total_commits', 0)
        
        # Details breakdown
        details = scores.get('details', [])
        jira_weighted = 0.0
        att_weighted = 0.0
        
        for d in details:
            if d.get('metric_key') == 'jira_sp':
                jira_weighted = d.get('weighted_score', 0.0)
            elif d.get('metric_key') == 'attendance':
                att_weighted = d.get('weighted_score', 0.0)
                
        overall = scores.get('overall', 0.0)
        
        report.append({
            "year": year,
            "user_id": uid,
            "full_name": name,
            "total_story_points": tot_sp,
            "founder_credit_sp": founder_credit,
            "founder_projects_count": founder_count,
            "raw_jira_issues": jira_issues,
            "gitlab_commits": commits,
            "attendance_days": att_days,
            "late_count": late_cnt,
            "team_max_sp": max_sp,
            "jira_weighted_score": jira_weighted,
            "attendance_weighted_score": att_weighted,
            "final_overall_score": overall
        })
        
    return sorted(report, key=lambda x: x['final_overall_score'], reverse=True)

report_2025 = get_detailed_year_report(2025)
report_2026 = get_detailed_year_report(2026)

with open('c:/Users/ATI-User/KPI-Dashboard/backend/detailed_report_2025_2026.json', 'w', encoding='utf-8') as f:
    f.write(json.dumps({"year_2025": report_2025, "year_2026": report_2026}, indent=2))

print("GENERATED DETAILED REPORT FOR 2025 AND 2026!")
