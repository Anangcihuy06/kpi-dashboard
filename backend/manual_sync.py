import requests
from database import SessionLocal
from models import IntegrationSetting, Sprint
from encrypt import decrypt_val

def manual_sync_sprints():
    db = SessionLocal()
    settings = db.query(IntegrationSetting).first()

    if settings and settings.jira_url and settings.jira_email:
        token = decrypt_val(settings.jira_token_encrypted)
        jira_auth = (settings.jira_email, token)
        
        print(f'Board ID: {settings.jira_board_id}')
        
        board_url = f'{settings.jira_url}/rest/agile/1.0/board/{settings.jira_board_id}/sprint'
        
        # Get active sprints
        print('Fetching active sprints...')
        response = requests.get(board_url, auth=jira_auth, params={'state': 'active'}, timeout=10)
        
        if response.status_code == 200:
            jira_sprints = response.json().get('values', [])
            print(f'Found {len(jira_sprints)} active sprint(s)')
            
            for js in jira_sprints:
                sprint_id_str = str(js.get('id'))
                existing = db.query(Sprint).filter(Sprint.jira_sprint_id == sprint_id_str).first()
                
                # Get dates
                from datetime import datetime
                s_date = datetime.now()
                e_date = datetime.now()
                if js.get('startDate'):
                    s_date = datetime.strptime(js.get('startDate').split('T')[0], '%Y-%m-%d')
                if js.get('endDate'):
                    e_date = datetime.strptime(js.get('endDate').split('T')[0], '%Y-%m-%d')
                
                if not existing:
                    print(f'Creating new sprint: {js.get("name")} (Jira ID: {sprint_id_str})')
                    new_sprint = Sprint(
                        jira_sprint_id=sprint_id_str,
                        sprint_name=js.get('name', 'Unknown'),
                        start_date=s_date,
                        end_date=e_date,
                        status='ACTIVE'
                    )
                    db.add(new_sprint)
                else:
                    print(f'Updating existing sprint: {js.get("name")} (Jira ID: {sprint_id_str})')
                    existing.sprint_name = js.get('name', 'Unknown')
                    existing.start_date = s_date
                    existing.end_date = e_date
                    existing.status = 'ACTIVE'
            
            db.commit()
            print('Active sprint sync completed!')
        else:
            print(f'Error fetching sprints: {response.status_code}')

        # Get closed sprints from current year
        print('\nFetching closed sprints from current year...')
        current_year = datetime.now().year
        response_closed = requests.get(board_url, auth=jira_auth, params={'state': 'closed'}, timeout=10)
        
        if response_closed.status_code == 200:
            jira_sprints = response_closed.json().get('values', [])
            closed_count = 0
            
            for js in jira_sprints:
                s_date = datetime.now()
                if js.get('startDate'):
                    s_date = datetime.strptime(js.get('startDate').split('T')[0], '%Y-%m-%d')
                
                # Only process current year sprints
                if s_date.year != current_year:
                    continue
                
                sprint_id_str = str(js.get('id'))
                existing = db.query(Sprint).filter(Sprint.jira_sprint_id == sprint_id_str).first()
                
                e_date = datetime.now()
                if js.get('endDate'):
                    e_date = datetime.strptime(js.get('endDate').split('T')[0], '%Y-%m-%d')
                
                if not existing:
                    print(f'Creating closed sprint: {js.get("name")} (Jira ID: {sprint_id_str})')
                    new_sprint = Sprint(
                        jira_sprint_id=sprint_id_str,
                        sprint_name=js.get('name', 'Unknown'),
                        start_date=s_date,
                        end_date=e_date,
                        status='CLOSED'
                    )
                    db.add(new_sprint)
                    closed_count += 1
                else:
                    print(f'Updating closed sprint: {js.get("name")} (Jira ID: {sprint_id_str})')
                    existing.sprint_name = js.get('name', 'Unknown')
                    existing.start_date = s_date
                    existing.end_date = e_date
                    existing.status = 'CLOSED'
            
            if closed_count > 0:
                db.commit()
                print(f'Closed sprint sync completed! Added: {closed_count} sprint(s)')
            else:
                print('No new closed sprints from current year to sync')

    db.close()

if __name__ == '__main__':
    manual_sync_sprints()