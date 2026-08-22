import requests
from datetime import datetime

url = "https://hris-api.atibusinessgroup.com/api/authenticate/mobile"
res = requests.post(url, json={
    "username": "01.05.13.500",
    "password": "rf1d"
}, timeout=8)
token = res.json().get("id_token")

page = 0
page_size = 2000
start_str = "2026-01-01"
end_str = "2026-12-31"

url_att = (
    f"https://hris-api.atibusinessgroup.com/api/app/users/attendances-new"
    f"?page={page}&size={page_size}&sort=clockin_timesheet"
    f"&startDate={start_str}&endDate={end_str}"
)

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json"
}

res_att = requests.get(url_att, headers=headers)
data = res_att.json()

if isinstance(data, dict):
    records = data.get("content", data.get("data", []))
else:
    records = data

unique_niks = set()
for rec in records:
    memployee = rec.get("memployee") or {}
    nik = memployee.get("nik") or rec.get("nik") or str(rec.get("employee_id", ""))
    unique_niks.add(nik)

print(records[0])
