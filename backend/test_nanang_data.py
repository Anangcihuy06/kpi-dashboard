import requests
import json
url = "https://hris-api.atibusinessgroup.com/api/authenticate/mobile"
res = requests.post(url, json={"username": "01.05.13.500", "password": "rf1d"}, timeout=8)
token = res.json().get("id_token", "")
headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
url_att = "https://hris-api.atibusinessgroup.com/api/app/users/attendances-new?page=0&size=200&startDate=2026-01-01&endDate=2026-12-31"
res_att = requests.get(url_att, headers=headers)
data = res_att.json()

nanang_count = 0
if isinstance(data, list):
    for rec in data:
        memployee = rec.get("memployee") or {}
        nik = memployee.get("nik") or rec.get("nik") or str(rec.get("employee_id", ""))
        if nik == "01.04.19.1905":
            nanang_count += 1
print("Nanang records:", nanang_count)
