import requests
import json
url = "https://hris-api.atibusinessgroup.com/api/authenticate/mobile"
res = requests.post(url, json={"username": "01.05.13.500", "password": "rf1d"}, timeout=8)
token = res.json().get("id_token", "")
headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

for page in range(5):
    url_att = f"https://hris-api.atibusinessgroup.com/api/app/users/attendances-new?page={page}&size=200&startDate=2026-01-01&endDate=2026-12-31"
    res_att = requests.get(url_att, headers=headers)
    data = res_att.json()
    if isinstance(data, list):
        print(f"Page {page} items: {len(data)}")
    elif isinstance(data, dict):
        print(f"Page {page} items: {len(data.get('content', data.get('data', [])))}")
