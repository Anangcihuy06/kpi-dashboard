import requests
import json
try:
    res = requests.post("http://localhost:8000/api/v1/auth/login", json={"username": "01.04.19.1905", "password": "rf1d"})
    print("Status:", res.status_code)
    print("Text:", res.text)
except Exception as e:
    print(e)
