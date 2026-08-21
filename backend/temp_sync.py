from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models
import requests
import os
from main import sync_subordinates_for_supervisor, app

@app.get("/api/v1/sync/force-subs/{supervisor_id}")
def force_sync_subs(supervisor_id: str, db: Session = Depends(get_db)):
    spv = db.query(models.User).filter(models.User.id == supervisor_id).first()
    if not spv:
        return {"error": "not found"}
        
    username = os.getenv("HRIS_SYSTEM_USERNAME")
    password = os.getenv("HRIS_SYSTEM_PASSWORD")
    
    res = requests.post("https://hris-api.atibusinessgroup.com/api/authenticate/mobile", json={
        "username": username,
        "password": password
    })
    token = res.json().get("id_token")
    
    processed = sync_subordinates_for_supervisor(db, spv, token)
    return {"processed": processed}
