import os

files_to_update = [
    'frontend/src/App.jsx',
    'frontend/src/components/Configurator.jsx',
    'frontend/src/components/Dashboard.jsx',
    'frontend/src/components/Subordinates.jsx'
]

for file_path in files_to_update:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        new_content = content.replace('"http://localhost:8000/', 'import.meta.env.VITE_API_URL + "/')
        new_content = new_content.replace('`http://localhost:8000/', '`${import.meta.env.VITE_API_URL}/')
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print('Updated ' + file_path)
    except Exception as e:
        print('Error updating ' + file_path + ': ' + str(e))
