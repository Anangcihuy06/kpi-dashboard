import requests

token = 'eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiIwMS4wNS4xMy41MDAiLCJsYXN0TmFtZSI6IkZhZGlsbGEgUG9lcm5hbWEiLCJmaXJzdE5hbWUiOiJSeWFuIiwiYXV0aCI6WyJNQU5BR0VSIl0sInVzZXIiOiI0ODIiLCJqdGkiOiI1ZTAzNzcwMi05YjUzLTQ5N2MtOTdjNi04MzEzNjY4NTNlNjciLCJpYXQiOjE3ODY5MTg5MzEsImV4cCI6MTc4NzAwNTMzMX0.nCA9qJAkbiGboxLLaTGuLCTHg-2GJU2sH5Tb-KQozrwou13kbrsTo2S0XiptnzoA0nmkPhQmh18-XXhnrSx02g'

user_data = {"id_token": token}

try:
    profile_url = "https://talent-backend.andreasbilly.com/api/app/users/profile"
    profile_resp = requests.get(profile_url, headers={"Authorization": f"Bearer {token}"}, timeout=10)
    print("PROFILE_STATUS:", profile_resp.status_code)
    if profile_resp.status_code == 200:
        profile_data = profile_resp.json()
        print("PROFILE_DATA keys:", profile_data.keys())
        print("PROFILE_GROUP:", profile_data.get("group"))
        print("PROFILE_DIVISION:", profile_data.get("division"))
        user_data.update(profile_data)
except Exception as e:
    print(f"Warning: Failed to fetch profile data: {e}")

print("FINAL USER_DATA group:", user_data.get("group"))
print("FINAL USER_DATA division:", user_data.get("division"))
