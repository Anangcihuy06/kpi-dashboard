import requests
import json
url = "https://hris-api.atibusinessgroup.com/api/authenticate/mobile"
res = requests.post(url, json={"username": "01.05.13.500", "password": "rf1d"}, timeout=8)
token = res.json().get("id_token", "")
headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
url_att = "https://hris-api.atibusinessgroup.com/api/app/users/attendances-new?page=0&size=10&startDate=2026-01-01&endDate=2026-12-31"
res_att = requests.get(url_att, headers=headers)
data = res_att.json()
print("Keys in response:", data.keys() if isinstance(data, dict) else "List")
if isinstance(data, dict):
    if 'data' in data:
        print("Len data:", len(data['data']))
    if 'content' in data:
        print("Len content:", len(data['content']))
elif isinstance(data, list):
    print("Len list:", len(data))
