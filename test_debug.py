import requests

res = requests.post("http://localhost:8000/api/v1/auth/debug_login", json={"username": "ryan", "password": "password"})
print(res.status_code)
if res.status_code == 200:
    data = res.json()
    print("AUTH RESPONSE:", data["auth_response"])
