#!/usr/bin/env python3
"""
Backfill employee division/group from HRIS.

The HRIS /overtime/request-data endpoint is token-scoped: each login returns that
user's OWN team. So to backfill correctly, log in as the manager whose team you
want to fix.

Usage:
  python fix_employee_divisions.py <manager_nik> <manager_password>

Credentials are passed at runtime per manager — nothing is hardcoded.
Run once per manager whose team needs to be re-synced.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import requests

from database import SessionLocal
import models

HRIS_LOGIN_URL = "https://talent-backend.andreasbilly.com/api/authenticate/mobile"
HRIS_OVERTIME_URL = "https://talent-backend.andreasbilly.com/api/app/overtime/request-data"
HRIS_PROFILE_URL = "https://talent-backend.andreasbilly.com/api/app/users/profile"


def login(username, password):
    if not username or not password:
        return None
    try:
        res = requests.post(HRIS_LOGIN_URL, json={"username": username, "password": password}, timeout=15)
        if res.status_code == 200:
            return res.json().get("id_token")
    except Exception as e:
        print(f"Login failed for {username}: {e}")
    return None


def fetch_profile(token):
    resp = requests.get(HRIS_PROFILE_URL, headers={"Authorization": f"Bearer {token}"}, timeout=10)
    return resp.json() if resp.status_code == 200 else None


def extract_division_group(profile_data):
    """Return (division_id, group_id, group_name) from a user profile."""
    div_id = None
    grp_id = None
    grp_name = None

    div_info = profile_data.get("division")
    if div_info and div_info.get("id"):
        div_id = str(div_info.get("id"))

    grp_info = profile_data.get("group")
    if grp_info and grp_info.get("id"):
        grp_id = str(grp_info.get("id"))
        grp_name = grp_info.get("group")

    return div_id, grp_id, grp_name


def sync_manager_team(username, token, nik):
    """Sync the team for the logged-in manager, assigning the manager's division/group."""
    db = SessionLocal()
    try:
        manager = db.query(models.User).filter(models.User.nik == nik).first()
        if not manager:
            print(f"ERROR: No local user found with NIK {nik}")
            return 0

        # Refresh manager's own division/group from their HRIS profile
        profile = fetch_profile(token)
        if profile:
            div_id, grp_id, grp_name = extract_division_group(profile)
            if div_id:
                manager.division_id = div_id
            if grp_id:
                manager.group_id = grp_id
                manager.group_name = grp_name
            db.commit()
            print(f"Manager profile: div={manager.division_id} grp={manager.group_id} {manager.group_name}")

        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        res = requests.get(HRIS_OVERTIME_URL, headers=headers, timeout=10)
        if res.status_code != 200:
            print(f"ERROR: Overtime API returned {res.status_code}")
            return 0
        employees = res.json().get("employee", [])

        s_div = manager.division_id
        s_grp = manager.group_id
        s_grp_name = manager.group_name

        processed = 0
        for emp in employees:
            emp_nik = emp.get("nik")
            emp_name = emp.get("name")
            emp_id = emp.get("id")

            if not emp_nik or emp_nik == manager.nik:
                continue

            sub = db.query(models.User).filter(models.User.nik == emp_nik).first()
            if sub:
                sub.supervisor_id = manager.id
                sub.employee_id = str(emp_id)
                sub.full_name = emp_name
                if s_div:
                    sub.division_id = s_div
                if s_grp:
                    sub.group_id = s_grp
                    sub.group_name = s_grp_name
                db.commit()
            else:
                temp_id = str(emp_id)
                id_exists = db.query(models.User).filter(models.User.id == temp_id).first()
                if id_exists:
                    temp_id = f"ext_{emp_id}"
                new_sub = models.User(
                    id=temp_id,
                    nik=emp_nik,
                    employee_id=str(emp_id),
                    full_name=emp_name,
                    roles=["EMPLOYEE"],
                    has_subordinates=False,
                    is_active=True,
                    division_id=s_div,
                    group_id=s_grp,
                    group_name=s_grp_name,
                    supervisor_id=manager.id,
                    jira_account_id=f"jira_user_{temp_id}",
                    gitlab_username=f"gitlab_user_{temp_id}"
                )
                db.add(new_sub)
                db.commit()
            processed += 1
            print(f"  {emp_name} ({emp_nik}) -> div={s_div} grp={s_grp} {s_grp_name}")

        # Unlink subordinates no longer returned by HRIS
        api_niks = {emp["nik"] for emp in employees if emp.get("nik")}
        db.query(models.User).filter(
            models.User.supervisor_id == manager.id,
            ~models.User.nik.in_(list(api_niks))
        ).update({"supervisor_id": None}, synchronize_session=False)
        db.commit()

        return processed
    finally:
        db.close()


def main():
    username = sys.argv[1] if len(sys.argv) > 1 else os.getenv("HRIS_SYSTEM_USERNAME", "")
    password = sys.argv[2] if len(sys.argv) > 2 else os.getenv("HRIS_SYSTEM_PASSWORD", "")

    if not username or not password:
        print("ERROR: Provide manager credentials or set HRIS_SYSTEM_USERNAME/PASSWORD.")
        print("Usage: python fix_employee_divisions.py <nik> <password>")
        sys.exit(1)

    print(f"Logging in as: {username}")
    token = login(username, password)
    if not token:
        print("ERROR: Login to HRIS failed.")
        sys.exit(1)

    n = sync_manager_team(username, token, username)
    print(f"Done. Employees processed: {n}")


if __name__ == "__main__":
    main()