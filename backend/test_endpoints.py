import requests
import json
url = "https://talent-backend.andreasbilly.com/api/authenticate/mobile"
res = requests.post(url, json={
    "username": "01.05.13.500",
    "password": "rf1d"
}, timeout=8)
token = res.json().get("id_token", "")
headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json"
}
for path in ["/api/app/users/attendances-new", "/api/v1/app/users/attendances-new", "/api/users/attendances-new", "/users/attendances-new"]:
    url_att = f"https://talent-backend.andreasbilly.com{path}?page=0&size=10"
    res_att = requests.get(url_att, headers=headers)
    print(f"{path}: {res_att.status_code}")
