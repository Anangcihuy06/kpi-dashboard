import requests, json

res = requests.get('http://localhost:8000/api/v1/kpi/yearly-performance?user_id=6518&year=2026')
if res.status_code == 200:
    data = res.json().get('data', {})
    print('=== Updated Yearly Performance for Nanang Wahyudi ===')
    print('Total Story Points:', data.get('summary', {}).get('total_story_points'))
    print('Total Issues Completed:', data.get('summary', {}).get('total_issues_completed'))
    print('Projects Count:', data.get('summary', {}).get('projects_count'))
    print('\nProjects List:')
    for p in data.get('projects', []):
        print(' -', p.get('name'))
    print('\nKPI Summary:')
    for kpi in data.get('kpis', []):
        print(f"KPI {kpi.get('indicator_code')}: Raw={kpi.get('raw_value')}, Score={kpi.get('calculated_score')}, FinalWeighted={kpi.get('final_weighted_score')}")
