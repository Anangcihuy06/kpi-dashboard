import requests
import json
url = "https://services-kpi-production.up.railway.app/api/v1/auth/login"
response = requests.post(url, json={"username": "nanang.wahyudi@atibusinessgroup.com", "password": "rf1d"})
print("Status:", response.status_code)
print("Headers:", response.headers)
print("Response text:", response.text[:200])
