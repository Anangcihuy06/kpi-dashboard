import logging
import json
import os
from typing import Dict, Any, List, Optional

logger = logging.getLogger("founder_engine")

AUTODETECTED_JSON_PATH = os.path.join(os.path.dirname(__file__), "autodetected_founders.json")

def _load_all_founders() -> List[Dict[str, Any]]:
    if os.path.exists(AUTODETECTED_JSON_PATH):
        try:
            with open(AUTODETECTED_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading autodetected_founders.json: {e}")
    return []

def get_founder_credits_for_user(user_id: str, target_year: Optional[int] = None) -> float:
    """
    Returns total Story Point Founder Architecture Credit for a user.
    If target_year is provided, returns credit for projects founded IN THAT SPECIFIC YEAR.
    """
    founders = _load_all_founders()
    total_credit = 0.0
    for pf in founders:
        if str(pf.get("founder_user_id")) == str(user_id):
            date_str = pf.get("initial_commit_date", "")
            inception_yr = date_str[:4] if date_str else None
            
            if target_year is not None:
                if inception_yr == str(target_year):
                    total_credit += float(pf.get("sp_credit", 150.0))
            else:
                total_credit += float(pf.get("sp_credit", 150.0))
                
    return total_credit

def get_founder_projects_info(user_id: str, target_year: Optional[int] = None) -> List[Dict[str, Any]]:
    """Returns detailed founder attribution info for projects created by user, optionally filtered by year."""
    founders = _load_all_founders()
    res = []
    for pf in founders:
        if str(pf.get("founder_user_id")) == str(user_id):
            date_str = pf.get("initial_commit_date", "")
            inception_yr = date_str[:4] if date_str else None
            
            if target_year is not None and inception_yr != str(target_year):
                continue
                
            res.append({
                "project_key": pf.get("project_name"),
                "founder_user_id": pf.get("founder_user_id"),
                "founder_name": pf.get("founder_name"),
                "sp_credit": pf.get("sp_credit", 150.0),
                "role_title": "Project Founder & Core Architect",
                "initial_commit_date": date_str
            })
    return res
