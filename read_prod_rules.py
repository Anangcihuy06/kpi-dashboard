import json

try:
    with open('prod_rules.json') as f:
        data = json.load(f)
    for rule in data.get('data', []):
        print(f"ID: {rule.get('rule_id')}, Name: {rule.get('name')}, Group: {rule.get('group_id')}, Active: {rule.get('is_active')}")
except Exception as e:
    print(e)
