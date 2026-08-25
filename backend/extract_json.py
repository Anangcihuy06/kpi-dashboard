import json
import re

with open(r'C:\Users\ATI-User\.gemini\antigravity-ide\brain\c66d482c-44e8-4863-bf05-f8bbf3b8bff5\.system_generated\logs\transcript.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        if data.get('type') == 'USER_INPUT' and '18.11.22.3063' in data.get('content', '') and '[' in data.get('content', ''):
            content = data['content']
            keys = set(re.findall(r'\"([a-zA-Z0-9_]+)\"\s*:', content))
            print("All keys found in JSON text:")
            for k in sorted(keys):
                print("-", k)
            break
