import json
import re

with open(r'C:\Users\ATI-User\.gemini\antigravity-ide\brain\c66d482c-44e8-4863-bf05-f8bbf3b8bff5\.system_generated\logs\transcript.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        if data.get('type') == 'USER_INPUT' and 'Adian' in data.get('content', ''):
            content = data['content']
            keys = set(re.findall(r'\"([a-zA-Z0-9_]+)\"\s*:', content))
            print('Found keys in user JSON:', keys)
            
            if 'hasSubordinates' in content:
                print('hasSubordinates IS in content')
            else:
                print('hasSubordinates IS NOT in content')
            break
