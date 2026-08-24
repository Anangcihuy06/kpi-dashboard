import requests
import json
url = "https://services-kpi-production.up.railway.app/api/v1/auth/login"
response = requests.post(url, json={"email": "test@test.com", "password": "test"})
print("Status:", response.status_code)
print("Headers:", response.headers)
print("Response:", response.text)
