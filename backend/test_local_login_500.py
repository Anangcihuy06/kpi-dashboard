import requests
import json
try:
    res = requests.post("http://localhost:8000/api/v1/auth/login", json={"username": "01.05.13.500", "password": "rf1d"})
    print("Status:", res.status_code)
    print("Text:", res.text)
except Exception as e:
    print(e)
