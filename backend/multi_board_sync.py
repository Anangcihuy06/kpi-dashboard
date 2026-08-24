import requests
from datetime import datetime
from sqlalchemy.orm import Session
import models
from encrypt import decrypt_val
import logging

logger = logging.getLogger("MultiProjectSync")

def sync_all_boards_sprints(db: Session, settings: models.IntegrationSetting):
    """
    Sync sprints from all configured Jira boards.
    Returns summary of synced sprints per board.
    """
    if not settings or not settings.jira_url or not settings.jira_token_encrypted:
        logger.warning("Jira settings incomplete. Cannot sync sprints.")
        return {}
    
    token = decrypt_val(settings.jira_token_encrypted)
    jira_auth = (settings.jira_email, token)
    
    # Get board IDs to sync (from settings)
    board_ids = settings.jira_board_ids if settings.jira_board_ids else []
    if settings.default_jira_board_id:
        board_ids.append(settings.default_jira_board_id)
    
    if not board_ids:
        logger.info("No Jira boards configured. Attempting auto-discovery...")
        try:
            resp = requests.get(f"{settings.jira_url}/rest/agile/1.0/board", auth=jira_auth, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for b in data.get('values', []):
                    board_ids.append(str(b['id']))
                logger.info(f"Auto-discovered {len(board_ids)} boards.")
            else:
                logger.warning(f"Failed to auto-discover boards: {resp.status_code}")
        except Exception as e:
            logger.error(f"Error during auto-discovery: {e}")
            
    if not board_ids:
        logger.warning("No Jira boards configured for sync and auto-discovery found none.")
        return {}
    
    # Remove duplicates
    board_ids = list(set(board_ids))
    
    results = {}
    
    for board_id in board_ids:
        logger.info(f"Syncing sprints from board {board_id}...")
        board_results = sync_board_sprints(db, settings, board_id, jira_auth)
        results[board_id] = board_results
        
        # Update board info in DB
        update_board_info(db, board_id, board_results, settings.jira_url, jira_auth)
    
    return results

def sync_board_sprints(db: Session, settings: models.IntegrationSetting, board_id: str, jira_auth: tuple):
    """Sync sprints from a specific Jira board."""
    board_url = f"{settings.jira_url}/rest/agile/1.0/board/{board_id}/sprint"
    
    results = {
        "board_id": board_id,
        "active": 0,
        "closed": 0,
        "errors": []
    }
    
    # Sync active sprints
    try:
        resp = requests.get(board_url, auth=jira_auth, params={"state": "active"}, timeout=10)
        if resp.status_code == 200:
            jira_sprints = resp.json().get("values", [])
            
            for js in jira_sprints:
                sprint_id_str = str(js.get("id"))
                existing = db.query(models.Sprint).filter(
                    models.Sprint.jira_sprint_id == sprint_id_str
                ).first()
                
                s_date = datetime.now()
                e_date = datetime.now()
                if js.get("startDate"):
                    s_date = datetime.strptime(js.get("startDate").split("T")[0], "%Y-%m-%d")
                if js.get("endDate"):
                    e_date = datetime.strptime(js.get("endDate").split("T")[0], "%Y-%m-%d")
                
                if not existing:
                    logger.info(f"Creating active sprint: {js.get('name')} (Board: {board_id}, Jira ID: {sprint_id_str})")
                    new_sprint = models.Sprint(
                        jira_sprint_id=sprint_id_str,
                        jira_board_id=board_id,
                        sprint_name=js.get("name", "Unknown"),
                        start_date=s_date,
                        end_date=e_date,
                        status="ACTIVE"
                    )
                    db.add(new_sprint)
                    results["active"] += 1
                else:
                    existing.sprint_name = js.get("name", "Unknown")
                    existing.start_date = s_date
                    existing.end_date = e_date
                    existing.status = "ACTIVE"
                    existing.jira_board_id = board_id
        else:
            error_msg = f"Failed to fetch active sprints from board {board_id}: {resp.status_code}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
            
    except Exception as e:
        error_msg = f"Exception syncing active sprints from board {board_id}: {str(e)}"
        logger.error(error_msg)
        results["errors"].append(error_msg)
    
    # Sync closed sprints from current year
    try:
        resp = requests.get(board_url, auth=jira_auth, params={"state": "closed"}, timeout=10)
        if resp.status_code == 200:
            jira_sprints = resp.json().get("values", [])
            current_year = datetime.now().year
            
            for js in jira_sprints:
                s_date = datetime.now()
                if js.get("startDate"):
                    s_date = datetime.strptime(js.get("startDate").split("T")[0], "%Y-%m-%d")
                
                # Only process current year sprints
                if s_date.year != current_year:
                    continue
                
                sprint_id_str = str(js.get("id"))
                existing = db.query(models.Sprint).filter(
                    models.Sprint.jira_sprint_id == sprint_id_str
                ).first()
                
                e_date = datetime.now()
                if js.get("endDate"):
                    e_date = datetime.strptime(js.get("endDate").split("T")[0], "%Y-%m-%d")
                
                if not existing:
                    logger.info(f"Creating closed sprint: {js.get('name')} (Board: {board_id}, Jira ID: {sprint_id_str})")
                    new_sprint = models.Sprint(
                        jira_sprint_id=sprint_id_str,
                        jira_board_id=board_id,
                        sprint_name=js.get("name", "Unknown"),
                        start_date=s_date,
                        end_date=e_date,
                        status="CLOSED"
                    )
                    db.add(new_sprint)
                    results["closed"] += 1
                else:
                    existing.sprint_name = js.get("name", "Unknown")
                    existing.start_date = s_date
                    existing.end_date = e_date
                    existing.status = "CLOSED"
                    existing.jira_board_id = board_id
        else:
            error_msg = f"Failed to fetch closed sprints from board {board_id}: {resp.status_code}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
            
    except Exception as e:
        error_msg = f"Exception syncing closed sprints from board {board_id}: {str(e)}"
        logger.error(error_msg)
        results["errors"].append(error_msg)
    
    db.commit()
    return results

def update_board_info(db: Session, board_id: str, results: dict, jira_url: str, jira_auth: tuple):
    """Update or create Jira board info in database."""
    try:
        # Get board details from Jira
        board_url = f"{jira_url}/rest/agile/1.0/board/{board_id}"
        resp = requests.get(board_url, auth=jira_auth, timeout=10)
        
        if resp.status_code == 200:
            board_data = resp.json()
            
            existing_board = db.query(models.JiraBoard).filter(
                models.JiraBoard.jira_board_id == board_id
            ).first()
            
            if not existing_board:
                board_info = models.JiraBoard(
                    jira_board_id=board_id,
                    board_name=board_data.get("name", "Unknown"),
                    board_type=board_data.get("type", "scrum"),
                    location=board_data.get("location", {}).get("name", "Unknown"),
                    last_synced=datetime.now()
                )
                db.add(board_info)
            else:
                existing_board.board_name = board_data.get("name", "Unknown")
                existing_board.board_type = board_data.get("type", "scrum")
                existing_board.location = board_data.get("location", {}).get("name", "Unknown")
                existing_board.last_synced = datetime.now()
            
            db.commit()
            
    except Exception as e:
        logger.warning(f"Failed to update board info for {board_id}: {str(e)}")

def get_user_active_sprint(db: Session, user: models.User, settings: models.IntegrationSetting = None):
    """
    Find the active sprint for a user based on their board assignments.
    Returns the active sprint or None.
    """
    if not settings:
        settings = db.query(models.IntegrationSetting).first()
    
    # Get user's board assignments
    user_board_ids = user.jira_board_ids if user.jira_board_ids else []
    if user.current_active_board:
        user_board_ids.append(user.current_active_board)
    
    if settings and settings.default_jira_board_id:
        user_board_ids.append(settings.default_jira_board_id)
    
    if not user_board_ids:
        # If no board assignments, try to find any active sprint
        active_sprints = db.query(models.Sprint).filter(
            models.Sprint.status == "ACTIVE"
        ).all()
        return active_sprints[0] if active_sprints else None
    
    # Remove duplicates and get unique board IDs
    unique_board_ids = list(set(user_board_ids))
    
    # Find active sprints from user's assigned boards
    for board_id in unique_board_ids:
        active_sprint = db.query(models.Sprint).filter(
            models.Sprint.jira_board_id == board_id,
            models.Sprint.status == "ACTIVE"
        ).first()
        
        if active_sprint:
            return active_sprint
    
    # If no active sprint found in assigned boards, return any active sprint
    active_sprints = db.query(models.Sprint).filter(
        models.Sprint.status == "ACTIVE"
    ).all()
    
    return active_sprints[0] if active_sprints else None