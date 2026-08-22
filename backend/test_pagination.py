import requests

url = "https://hris-api.atibusinessgroup.com/api/authenticate/mobile"
res = requests.post(url, json={"username": "01.05.13.500", "password": "rf1d"}, timeout=8)
token = res.json().get("id_token")

for page in range(3):
    url2 = f"https://hris-api.atibusinessgroup.com/api/app/users/attendances-new?page={page}&size=200&sort=clockin_timesheet&startDate=2026-01-01&endDate=2026-12-31"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    res2 = requests.get(url2, headers=headers, timeout=10)
    data = res2.json()
    if isinstance(data, list):
        print(f"Page {page} returned list of {len(data)}")
    elif isinstance(data, dict):
        content = data.get("content", data.get("data", []))
        print(f"Page {page} returned dict. content len: {len(content)}, last: {data.get('last')}, totalElements: {data.get('totalElements')}")
    else:
        print(f"Page {page} returned other")
