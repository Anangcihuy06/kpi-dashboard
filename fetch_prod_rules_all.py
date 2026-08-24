import json, urllib.request
try:
    req = urllib.request.Request('https://services-kpi-production.up.railway.app/api/v1/kpi-rules?division_id=23')
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
    for rule in data.get('data', []):
        print(f"ID: {rule.get('rule_id')}, Name: {rule.get('name')}, Group: {rule.get('group_id')}, Active: {rule.get('is_active')}, Version: {rule.get('version')}")
except Exception as e:
    print(e)
