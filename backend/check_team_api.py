import requests, json

res = requests.get('http://localhost:8000/api/v1/kpi/team-yearly?user_id=482&year=2026')
if res.status_code == 200:
    subs = res.json().get('data', [])
    print(f"=== TEAM YEARLY PERFORMANCE ({len(subs)} subordinates) ===")
    for s in subs:
        score_info = s.get('kpi_scores', {})
        print(f"User {s.get('user_id')} ({s.get('full_name')}): Overall Score = {score_info.get('overall')}, SP = {s.get('summary', {}).get('total_story_points')}")
else:
    print("Error:", res.status_code, res.text)
