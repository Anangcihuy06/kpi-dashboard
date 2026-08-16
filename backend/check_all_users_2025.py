import requests, json

print("=== CHECKING YEAR 2025 PERFORMANCE FOR ALL TEAM MEMBERS ===")

# 1. Team Yearly Endpoint
r_team = requests.get('http://localhost:8000/api/v1/kpi/team-yearly?user_id=482&year=2025')
if r_team.status_code == 200:
    team_data = r_team.json().get('data', [])
    print(f"\n--- TEAM YEARLY LEADERBOARD 2025 ({len(team_data)} members) ---")
    for member in team_data:
        uid = member.get('user_id')
        name = member.get('full_name')
        scores = member.get('kpi_scores', {})
        summary = member.get('summary', {})
        sp = summary.get('total_story_points', 0)
        att = summary.get('total_attendance_days', 0)
        overall = scores.get('overall', 0)
        founder_credit = summary.get('founder_architecture_credit', 0)
        print(f"User {uid} ({name}): Overall = {overall} | SP = {sp} (Founder Credit = {founder_credit}) | Attendance Days = {att}")

# 2. Individual Check for Billy
r_billy = requests.get('http://localhost:8000/api/v1/kpi/yearly-performance?user_id=9615&year=2025')
if r_billy.status_code == 200:
    bdata = r_billy.json().get('data', {})
    print("\n--- INDIVIDUAL DETAIL FOR ANDREAS BILLY SUTANDI (2025) ---")
    print("Summary:", json.dumps(bdata.get('summary'), indent=2))
    print("Scores:", json.dumps(bdata.get('kpi_scores'), indent=2))
