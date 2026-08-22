import json, urllib.request

try:
    req = urllib.request.Request('https://services-kpi-production.up.railway.app/api/v1/kpi-rules?division_id=23')
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        
    for rule in data.get('data', []):
        if str(rule.get('group_id')) == '496':
            print(f"ID: {rule.get('rule_id')}, Name: {rule.get('name')}, Group: {rule.get('group_id')}, Active: {rule.get('is_active')}, Version: {rule.get('version')}")
            for m in rule.get('metrics', []):
                if 'COMPLEXITY' in m.get('metric_key', '').upper():
                    print(f"  Target: {m.get('variables', {}).get('target_complexity_pts')}")
except Exception as e:
    print(e)
