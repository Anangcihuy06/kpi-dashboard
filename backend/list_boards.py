import requests
from database import SessionLocal
from models import IntegrationSetting
from encrypt import decrypt_val

def list_available_boards():
    db = SessionLocal()
    settings = db.query(IntegrationSetting).first()

    if settings:
        token = decrypt_val(settings.jira_token_encrypted)
        jira_auth = (settings.jira_email, token)
        
        print(f'Getting all available boards for {settings.jira_email}...\n')
        
        # Get all boards
        boards_url = f'{settings.jira_url}/rest/agile/1.0/board'
        
        try:
            response = requests.get(boards_url, auth=jira_auth, timeout=10)
            print(f'Status Code: {response.status_code}')
            
            if response.status_code == 200:
                data = response.json()
                values = data.get('values', [])
                print(f'Found {len(values)} board(s):\n')
                
                for board in values:
                    print(f'Board ID: {board.get("id")}')
                    print(f'Name: {board.get("name")}')
                    print(f'Type: {board.get("type")}')
                    print(f'Location: {board.get("location", {}).get("name")}')
                    print('-' * 50)
            else:
                print(f'Error response: {response.text}')
                
        except Exception as e:
            print(f'Connection error: {str(e)}')

    db.close()

if __name__ == '__main__':
    list_available_boards()