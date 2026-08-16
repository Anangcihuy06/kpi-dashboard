import requests

res = requests.get('http://localhost:8000/api/v1/kpi/team-yearly?user_id=482&year=2026')
if res.status_code == 200:
    data = res.json().get("data", [])
    for d in data:
        if d["nik"] == "01.04.19.1905":
            print("Nanang Data:")
            print(f"ID: {d['user_id']}")
            print(f"Attendance: {d['summary']['total_attendance_days']}")
            print(f"Commits: {d['summary']['total_commits']}")
            print(f"Issues: {d['summary']['total_issues_completed']}")
            print(f"SP: {d['summary']['total_story_points']}")
else:
    print(f"Error {res.status_code}: {res.text}")
