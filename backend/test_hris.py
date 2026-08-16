import requests

login_res = requests.post("https://hris-api.atibusinessgroup.com/api/v1/auth/login", json={"email":"nanang.wahyudi@atibusinessgroup.com","password":"rf1d"})
print("Login status:", login_res.status_code)
print("Login text:", login_res.text[:200])
