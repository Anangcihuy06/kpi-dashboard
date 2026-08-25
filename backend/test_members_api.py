"""Quick test to verify the new /api/app/users/members endpoint returns data."""
import requests
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Login first to get token
login_url = "https://hris-api.atibusinessgroup.com/api/authenticate/mobile"
members_url = "https://hris-api.atibusinessgroup.com/api/app/users/members"

# Use env credentials or hardcode for testing
username = os.getenv("TEST_USER", "nanang.wahyudi@atibusinessgroup.com")
password = os.getenv("TEST_PASS", "rf1d")

print(f"Logging in as {username}...")
login_res = requests.post(login_url, json={"username": username, "password": password}, timeout=15)
if login_res.status_code != 200:
    print(f"Login failed: {login_res.status_code}")
    sys.exit(1)

token = login_res.json().get("id_token")
if not token:
    print("No token received")
    sys.exit(1)

print(f"Login success, token: {token[:20]}...")

# Fetch members
headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
members_res = requests.get(members_url, headers=headers, timeout=15)
print(f"Members API status: {members_res.status_code}")

if members_res.status_code == 200:
    members = members_res.json()
    print(f"Type: {type(members)}, Count: {len(members) if isinstance(members, list) else 'N/A'}")
    
    def print_tree(member, indent=0):
        nik = member.get("nik", "?")
        first = member.get("firstName", "")
        last = member.get("lastName", "")
        pos = member.get("position", {})
        pos_name = pos.get("positionName", "?") if pos else "?"
        group = member.get("group", {})
        grp_name = group.get("group", "?") if group else "?"
        children = member.get("children", [])
        prefix = "  " * indent
        print(f"{prefix}├─ [{nik}] {first} {last} | {pos_name} | Group: {grp_name} | Children: {len(children)}")
        for child in children:
            print_tree(child, indent + 1)
    
    for m in members:
        print_tree(m)
else:
    print(f"Error: {members_res.text[:500]}")
