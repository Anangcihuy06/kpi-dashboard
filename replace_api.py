import os
import glob

search_str = "https://talent-backend.andreasbilly.com/api"
replace_str = "https://talent-backend.andreasbilly.com/api"

for filepath in glob.glob("backend/**/*.py", recursive=True):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if search_str in content:
            new_content = content.replace(search_str, replace_str)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Replaced in {filepath}")
    except Exception as e:
        pass
