import os
import sys
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
import models
from main import sync_subordinates_for_supervisor

def run():
    db = SessionLocal()
    spv = db.query(models.User).filter(models.User.id == "482").first()
    if not spv:
        print("Nanang not found in db")
        return

    username = os.getenv("HRIS_SYSTEM_USERNAME")
    password = os.getenv("HRIS_SYSTEM_PASSWORD")
    
    res = requests.post("https://talent-backend.andreasbilly.com/api/authenticate/mobile", json={
        "username": username,
        "password": password
    })
    token = res.json().get("id_token")
    if not token:
        print("Failed to get token")
        return
        
    print("Got token. Running sync...")
    processed = sync_subordinates_for_supervisor(db, spv, token)
    print(f"Processed: {processed}")
    
run()
