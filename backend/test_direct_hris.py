import requests
import json
url = "https://talent-backend.andreasbilly.com/api/authenticate/mobile"
res = requests.post(url, json={
    "username": "01.05.13.500",
    "password": "rf1d"
}, timeout=8)
print("Auth Status:", res.status_code)
if res.status_code == 200:
    token = res.json().get("id_token", "")
    print("Token ok:", bool(token))
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    url_att = "https://hris-api.atibusinessgroup.com/app/users/attendances-new?page=0&size=10&sort=clockin_timesheet"
    res_att = requests.get(url_att, headers=headers)
    print("Att Status:", res_att.status_code)
    print("Att Data:", res_att.text[:200])
