import requests
from database import SessionLocal
from models import IntegrationSetting
from encrypt import decrypt_val

def test_board_sprints(board_id):
    db = SessionLocal()
    settings = db.query(IntegrationSetting).first()

    if settings:
        token = decrypt_val(settings.jira_token_encrypted)
        jira_auth = (settings.jira_email, token)
        
        print(f'Testing board {board_id} for sprints...\n')
        
        # Get sprints from board
        sprint_url = f'{settings.jira_url}/rest/agile/1.0/board/{board_id}/sprint'
        
        try:
            # Test active sprints first
            response = requests.get(sprint_url, auth=jira_auth, params={'state': 'active'}, timeout=10)
            print(f'Active sprints - Status: {response.status_code}')
            
            if response.status_code == 200:
                data = response.json()
                values = data.get('values', [])
                print(f'Found {len(values)} active sprint(s)')
                
                for sprint in values[:3]:
                    print(f'  - {sprint.get("name")} (ID: {sprint.get("id")})')
                    print(f'    State: {sprint.get("state")}')
            
            # Test closed sprints
            response_closed = requests.get(sprint_url, auth=jira_auth, params={'state': 'closed'}, timeout=10)
            print(f'\nClosed sprints - Status: {response_closed.status_code}')
            
            if response_closed.status_code == 200:
                data = response_closed.json()
                values = data.get('values', [])
                print(f'Found {len(values)} closed sprint(s)')
                
                for sprint in values[:3]:
                    print(f'  - {sprint.get("name")} (ID: {sprint.get("id")})')
                    print(f'    State: {sprint.get("state")}')
                    
        except Exception as e:
            print(f'Error: {str(e)}')

    db.close()

if __name__ == '__main__':
    # Test some scrum boards
    test_board_sprints(1)    # GA board (scrum)
    test_board_sprints(61)   # OPA PL (scrum)
    test_board_sprints(59)   # GOV0 board (scrum)
    test_board_sprints(638)  # AATH board (scrum)