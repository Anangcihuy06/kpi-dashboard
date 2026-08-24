import requests

url = "https://talent-backend.andreasbilly.com/api/authenticate/mobile"
res = requests.post(url, json={"username": "01.05.13.500", "password": "rf1d"}, timeout=8)
token = res.json().get("id_token")

url2 = "https://talent-backend.andreasbilly.com/api/app/users/attendances-new?page=0&size=2000&sort=clockin_timesheet&startDate=2026-01-01&endDate=2026-12-31"
headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
res2 = requests.get(url2, headers=headers, timeout=10)
data = res2.json()

if isinstance(data, list):
    records = data
elif isinstance(data, dict):
    records = data.get("content", data.get("data", []))
else:
    records = []

nanang_count = 0
for r in records:
    mem = r.get("memployee") or {}
    nik = mem.get("nik") or r.get("nik") or str(r.get("employee_id", ""))
    if nik == "01.04.19.1905":
        nanang_count += 1
        
print(f"Total records fetched: {len(records)}")
print(f"Nanang attendance count: {nanang_count}")
