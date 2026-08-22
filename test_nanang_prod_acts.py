import requests
import json
import urllib3

urllib3.disable_warnings()

BASE_URL = "https://services-kpi-production.up.railway.app/api/v1"

def login():
    res = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "01.05.13.500",
        "password": "rf1d"
    })
    return res.json().get("token")

def run():
    token = login()
    headers = {"Authorization": f"Bearer {token}"}
    
    # We found Nanang's ID is probably 6518. Let's check team members first to be sure
    res = requests.get(f"{BASE_URL}/kpi/team-yearly?user_id=482&year=2026&direct_only=true", headers=headers)
    if not res.ok:
        print("Fetch failed:", res.text)
        return
        
    data = res.json()
    members = data.get("team_members", [])
    nanang = next((m for m in members if "Nanang" in m.get("user_name", "")), None)
    if not nanang:
        nanang_id = "6518" # fallback
    else:
        nanang_id = nanang["user_id"]
        
    print(f"Fetching activities for Nanang ({nanang_id})...")
    res = requests.get(f"{BASE_URL}/kpi/activities?user_id={nanang_id}&from_date=2026-01-01&to_date=2026-12-31", headers=headers)
    if res.ok:
        acts = res.json()
        print(f"Total activities: {len(acts)}")
        jira_acts = [a for a in acts if a.get("source") == "jira" and a.get("activity_type") in ("issue_done", "issue_completed")]
        print(f"Total Jira issues completed: {len(jira_acts)}")
        
        # print the most recent 5 ones
        jira_acts.sort(key=lambda x: x.get("activity_date", ""), reverse=True)
        for a in jira_acts[:10]:
            print(f"- {a.get('activity_date')}: {a.get('activity_metadata', {}).get('issue_summary')} (SP: {a.get('story_points')})")
    else:
        print("Activities fetch failed:", res.text)
        
if __name__ == "__main__":
    run()
