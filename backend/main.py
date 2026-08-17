import requests
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging
logger = logging.getLogger("main")
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel

# In-memory store for supervisor HRIS tokens
_supervisor_token_store = {}

from database import engine, get_db
import models
from engine import DynamicKPIEngine, evaluate_kpi_formula
from encrypt import encrypt_val, decrypt_val
import os
from contextlib import asynccontextmanager
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache
from scheduler import init_scheduler
from sync_service import sync_attendance_for_sprint, get_system_token
from multi_board_sync import sync_all_boards_sprints, get_user_active_sprint
from comprehensive_sync import sync_user_comprehensive, calculate_daily_aggregated_kpi

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables and seed data if empty
    from database import engine, SessionLocal
    import models
    from seed import seed_data
    from sqlalchemy import text
    
    # Auto-migrate new columns - wrapped in try/except so app starts even if DB is full
    try:
        try:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN group_id VARCHAR(50);"))
        except Exception:
            pass
        try:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN group_name VARCHAR(150);"))
        except Exception:
            pass
        try:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE kpi_rules ADD COLUMN group_id VARCHAR(50);"))
        except Exception:
            pass
        try:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE kpi_rules ADD COLUMN group_name VARCHAR(150);"))
        except Exception:
            pass

        models.Base.metadata.create_all(bind=engine)
        
        db = SessionLocal()
        if not db.query(models.User).first():
            print("Database is empty, running seed script...")
            seed_data()
        db.close()
    except Exception as e:
        print(f"WARNING: DB initialization failed (DB may be full): {e}")
        print("App will start anyway - use /api/v1/db/cleanup to fix DB issues")

    FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")
    # init_scheduler() is removed for standalone worker approach
    yield

app = FastAPI(title="Dynamic KPI Dashboard API", lifespan=lifespan)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000",
        "https://kpi-dashboard-xi-murex.vercel.app",
        os.environ.get("FRONTEND_URL", "https://kpi-dashboard-xi-murex.vercel.app"),
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

import webhooks
app.include_router(webhooks.router)

# Pydantic Schemas
class LoginRequest(BaseModel):
    username: str
    password: str

class TestFormulaRequest(BaseModel):
    formula: str
    context: Dict[str, float]

class MetricRuleInput(BaseModel):
    metric_key: str
    weight: float
    calc_type: str
    formula_expression: str
    variables: Dict[str, Any] = {}
    cap_score: float = 120.0

class KPIRuleInput(BaseModel):
    division_id: str
    group_id: Optional[str] = None
    group_name: Optional[str] = None
    name: str
    metrics: List[MetricRuleInput]

class IntegrationSettingInput(BaseModel):
    jira_url: str
    jira_email: str
    jira_token: Optional[str] = None  # If None, keep existing token
    jira_board_ids: Optional[List[str]] = None  # List of board IDs to sync
    default_jira_board_id: Optional[str] = None  # Default board for users without assignments
    jira_board_id: Optional[str] = None # Legacy support
    jira_sp_field: str = "customfield_10016"
    
    gitlab_url: str = "https://gitlab.com"
    gitlab_token: Optional[str] = None  # If None, keep existing token

class UserBoardAssignmentInput(BaseModel):
    user_id: str
    jira_board_ids: List[str] = []
    current_active_board: Optional[str] = None

# Helper: Recursive Subordinates Lookup
def get_recursive_subordinates(db: Session, supervisor_id: str) -> List[models.User]:
    direct_subs = db.query(models.User).filter(models.User.supervisor_id == supervisor_id).all()
    all_subs = list(direct_subs)
    for sub in direct_subs:
        all_subs.extend(get_recursive_subordinates(db, sub.id))
    return all_subs

# Endpoints
@app.post("/api/v1/auth/login")
def login(payload: LoginRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    external_url = "https://hris-api.atibusinessgroup.com/api/authenticate/mobile"
    try:
        response = requests.post(external_url, json={
            "username": payload.username,
            "password": payload.password
        }, timeout=30)
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Gagal menghubungi server autentikasi eksternal: {str(e)}"
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username atau password salah (Autentikasi Eksternal Gagal)"
        )

    user_data = response.json()
    
    token = user_data.get("id_token")
    if token:
        try:
            profile_url = "https://hris-api.atibusinessgroup.com/api/app/users/profile"
            profile_resp = requests.get(profile_url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
            print("PROFILE_STATUS:", profile_resp.status_code)
            if profile_resp.status_code == 200:
                profile_data = profile_resp.json()
                print("PROFILE_KEYS:", profile_data.keys())
                print("PROFILE_GROUP:", profile_data.get("group"))
                print("PROFILE_DIVISION:", profile_data.get("division"))
                user_data.update(profile_data)
        except Exception as e:
            print(f"Warning: Failed to fetch profile data: {e}")
    
    # Check if division exists, if not create a default one
    default_div = db.query(models.Division).filter(models.Division.code == "IT").first()
    if not default_div:
        default_div = models.Division(code="IT", name="IT & Engineering")
        db.add(default_div)
        db.commit()
        db.refresh(default_div)

    # Upsert User to Local SQLite DB
    user_id = str(user_data.get("user_id"))
    nik = user_data.get("nik")
    employee_id = user_data.get("employeeId")
    full_name = f"{user_data.get('firstName', '')} {user_data.get('lastName', '')}".strip()
    roles = user_data.get("roles", [])
    has_subs = user_data.get("hasSubordinates", False)
    
    # Handle supervisor link
    supervisor_id = None
    direct_spv = user_data.get("directSpv")
    if direct_spv and direct_spv.get("id") and nik != "01.05.13.500":
        spv_id = str(direct_spv["id"])
        spv_in_db = db.query(models.User).filter(models.User.id == spv_id).first()
        if not spv_in_db:
            spv_name = direct_spv.get("name") or direct_spv.get("fullName") or f"Supervisor {spv_id}"
            new_spv = models.User(
                id=spv_id,
                nik=f"SPV.{spv_id}",
                full_name=spv_name,
                roles=["MANAGER"],
                has_subordinates=True,
                is_active=True
            )
            db.add(new_spv)
            db.commit()
        supervisor_id = spv_id

    # Find or Create User
    user = db.query(models.User).filter(models.User.nik == nik).first()
    if not user:
        user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        user = models.User(
            id=user_id,
            nik=nik,
            full_name=full_name or f"User {user_id}",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if user.id != user_id:
            old_id = user.id
            db.execute(text("UPDATE users SET supervisor_id = :new_id WHERE supervisor_id = :old_id"), {"new_id": user_id, "old_id": old_id})
            db.execute(text("UPDATE employee_identity SET user_id = :new_id WHERE user_id = :old_id"), {"new_id": user_id, "old_id": old_id})
            db.execute(text("UPDATE activities SET user_id = :new_id WHERE user_id = :old_id"), {"new_id": user_id, "old_id": old_id})
            db.execute(text("UPDATE kpi_employee_daily SET user_id = :new_id WHERE user_id = :old_id"), {"new_id": user_id, "old_id": old_id})
            db.execute(text("UPDATE attendance_records SET user_id = :new_id WHERE user_id = :old_id"), {"new_id": user_id, "old_id": old_id})
            db.execute(text("UPDATE raw_metrics_data SET user_id = :new_id WHERE user_id = :old_id"), {"new_id": user_id, "old_id": old_id})
            db.execute(text("UPDATE sprint_kpi_scores SET user_id = :new_id WHERE user_id = :old_id"), {"new_id": user_id, "old_id": old_id})
            db.execute(text("UPDATE users SET id = :new_id WHERE id = :old_id"), {"new_id": user_id, "old_id": old_id})
            db.commit()
            db.expire_all()
            user = db.query(models.User).filter(models.User.id == user_id).first()

    user.employee_id = employee_id
    user.full_name = full_name
    user.roles = roles
    user.has_subordinates = has_subs
    user.supervisor_id = supervisor_id
    
    group_info = user_data.get("group")
    if group_info:
        user.group_id = str(group_info.get("id")) if group_info.get("id") else None
        user.group_name = group_info.get("group")

    div_info = user_data.get("division")
    if div_info and div_info.get("id"):
        div_id = str(div_info.get("id"))
        # Pastikan divisi ada di database
        div_db = db.query(models.Division).filter(models.Division.id == div_id).first()
        if not div_db:
            div_db = models.Division(
                id=div_id,
                code=div_info.get("divCode", "UNKNOWN"),
                name=div_info.get("division", "Unknown Division")
            )
            db.add(div_db)
            db.commit()
            db.refresh(div_db)
        user.division_id = div_id
    elif not user.division_id:
        user.division_id = default_div.id

    # Provide defaults for external mappings if they are empty
    if not user.jira_account_id:
        user.jira_account_id = f"jira_user_{user_id}"
    if not user.gitlab_username:
        user.gitlab_username = f"gitlab_user_{user_id}"

    db.commit()
    db.refresh(user)

    # Save token & sync subordinates in BACKGROUND — login returns immediately
    id_token = user_data.get("id_token")
    
    if id_token and user.id:
        # Store token in memory for later use (attendance sync, etc.)
        _supervisor_token_store[user.id] = {
            "token": id_token,
            "expires_at": datetime.now() + timedelta(hours=6)
        }
    
    def _background_sync_subordinates(supervisor_user_id: str, supervisor_nik: str, token: str):
        """Run subordinate sync in background so login is not blocked."""
        from database import SessionLocal
        _db = SessionLocal()
        try:
            hdr = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
            url = "https://hris-api.atibusinessgroup.com/api/app/overtime/request-data"
            res = requests.get(url, headers=hdr, timeout=8)
            if res.status_code == 200:
                employees = res.json().get("employee", [])
                for emp in employees:
                    emp_nik = emp.get("nik")
                    emp_name = emp.get("name")
                    emp_id = emp.get("id")
                    if not emp_nik or emp_nik == supervisor_nik:
                        continue
                    sub = _db.query(models.User).filter(models.User.nik == emp_nik).first()
                    if sub:
                        sub.supervisor_id = supervisor_user_id
                        sub.employee_id = str(emp_id)
                        sub.full_name = emp_name
                        _db.commit()
                    else:
                        new_sub = models.User(
                            id=f"api_{emp_id}",
                            nik=emp_nik,
                            full_name=emp_name,
                            supervisor_id=supervisor_user_id,
                            employee_id=str(emp_id),
                            roles=["ROLE_USER"],
                            is_active=True,
                            jira_account_id=f"jira_user_api_{emp_id}",
                            gitlab_username=f"gitlab_user_api_{emp_id}"
                        )
                        _db.add(new_sub)
                        _db.commit()
        except Exception as e:
            print(f"[BG Sync] Subordinate sync failed for {supervisor_user_id}: {e}")
        finally:
            _db.close()
    
    # Trigger background sync for managers/supervisors only
    is_manager = user.has_subordinates or "MANAGER" in (user.roles or []) or "ROLE_ADMIN" in (user.roles or [])
    if id_token and is_manager:
        background_tasks.add_task(_background_sync_subordinates, user.id, user.nik, id_token)

    return {
        "status": "success",
        "token": user_data.get("id_token"),
        "user": {
            "id": user.id,
            "nik": user.nik,
            "employeeId": user.employee_id,
            "fullName": user.full_name,
            "roles": user.roles,
            "hasSubordinates": user.has_subordinates,
            "division_id": user.division_id,
            "group_id": user.group_id,
            "group_name": user.group_name,
            "supervisor_id": user.supervisor_id
        }
    }

class UpdateUserEmailRequest(BaseModel):
    email: str

@app.put("/api/v1/users/{user_id}/email")
def update_user_email(user_id: str, payload: UpdateUserEmailRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    user.email = payload.email
    db.commit()
    db.refresh(user)
    return {"status": "success", "message": "Email berhasil diperbarui", "email": user.email}

@app.post("/api/v1/auth/debug_login")
def debug_login(payload: LoginRequest):
    external_url = "https://hris-api.atibusinessgroup.com/api/authenticate/mobile"
    response = requests.post(external_url, json={"username": payload.username, "password": payload.password}, timeout=10)
    user_data = response.json()
    token = user_data.get("id_token")
    profile_data = None
    if token:
        profile_url = "https://hris-api.atibusinessgroup.com/api/app/users/profile"
        profile_resp = requests.get(profile_url, headers={"Authorization": f"Bearer {token}"}, timeout=10)
        try:
            profile_data = profile_resp.json()
        except:
            profile_data = profile_resp.text
    return {"auth_response": user_data, "profile_response": profile_data}

@app.get("/api/v1/auth/verify")
def verify_local_session(user_id: str, db: Session = Depends(get_db)):
    """
    Quick local session check — no HRIS call needed.
    Returns user data if the user_id exists in local SQLite DB.
    Used by frontend to silently restore sessions without hitting HRIS.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Session tidak valid")
    return {
        "status": "valid",
        "user": {
            "id": user.id,
            "nik": user.nik,
            "employeeId": user.employee_id,
            "fullName": user.full_name,
            "roles": user.roles,
            "hasSubordinates": user.has_subordinates,
            "division_id": user.division_id,
            "group_id": user.group_id,
            "group_name": user.group_name,
            "supervisor_id": user.supervisor_id
        }
    }

@app.post("/api/v1/attendance/sync-year")
def sync_attendance_year(
    supervisor_id: str,
    year: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trigger yearly attendance sync for all subordinates of a supervisor.
    Uses the HRIS admin endpoint per-NIK, paginated. Results cached in SQLite.
    """
    from sync_service import sync_attendance_for_year
    from sync_engine import create_sync_job, update_job_progress, mark_job_completed, mark_job_failed
    
    supervisor = db.query(models.User).filter(models.User.id == supervisor_id).first()
    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor tidak ditemukan")
    
    subordinates = db.query(models.User).filter(models.User.supervisor_id == supervisor_id).all()
    if not subordinates:
        return {"status": "ok", "message": "Tidak ada bawahan untuk disinkronisasi", "count": 0}
        
    job_id = create_sync_job(db, supervisor_id, "ATTENDANCE_SYNC_YEAR")
    
    def _do_sync(j_id, sub_list, y):
        from database import SessionLocal
        _db = SessionLocal()
        try:
            update_job_progress(_db, j_id, 10, "RUNNING")
            sync_attendance_for_year(_db, sub_list, y)
            mark_job_completed(_db, j_id, {"count": len(sub_list), "year": y})
        except Exception as e:
            mark_job_failed(_db, j_id, str(e))
        finally:
            _db.close()
    
    background_tasks.add_task(_do_sync, job_id, subordinates, year)
    return {
        "status": "syncing",
        "message": f"Sinkronisasi attendance {year} dimulai untuk {len(subordinates)} karyawan",
        "count": len(subordinates),
        "year": year,
        "job_id": job_id
    }

@app.get("/api/v1/divisions")
def get_divisions(db: Session = Depends(get_db)):
    return db.query(models.Division).all()

@app.get("/api/v1/user-groups")
def get_user_groups(division_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(
        models.User.group_id, 
        models.User.group_name
    ).filter(
        models.User.group_id.isnot(None),
        models.User.group_id != ""
    )
    
    if division_id:
        query = query.filter(models.User.division_id == division_id)
        
    # Get unique groups
    groups = query.distinct().all()
    
    return [{"id": g.group_id, "name": g.group_name} for g in groups]

@app.get("/api/v1/sprints")
def get_sprints(db: Session = Depends(get_db)):
    # Sprint sync is now handled smoothly in the background by APScheduler in scheduler.py
    return db.query(models.Sprint).order_by(models.Sprint.start_date.desc()).all()

@app.get("/api/v1/kpi/my-performance")
@cache(expire=60)
def get_my_performance(user_id: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    scores = db.query(models.SprintKPIScore).filter(models.SprintKPIScore.user_id == user_id).all()
    
    results = []
    for s in scores:
        sprint = db.query(models.Sprint).filter(models.Sprint.id == s.sprint_id).first()
        raw_m = db.query(models.RawMetricsData).filter(
            models.RawMetricsData.user_id == user_id,
            models.RawMetricsData.sprint_id == s.sprint_id
        ).first()

        results.append({
            "sprint_id": s.sprint_id,
            "sprint_name": sprint.sprint_name if sprint else "Unknown Sprint",
            "final_score": float(s.final_score),
            "breakdown": s.breakdown_details,
            "raw_metrics": raw_m.metrics_payload if raw_m else {},
            "calculated_at": s.calculated_at
        })
    
    return {
        "user_id": user_id,
        "full_name": user.full_name,
        "scores": results
    }

@app.get("/api/v1/kpi/subordinates")
@cache(expire=60)
def get_subordinates_list(supervisor_id: str, db: Session = Depends(get_db)):
    spv = db.query(models.User).filter(models.User.id == supervisor_id).first()
    if not spv:
        raise HTTPException(status_code=404, detail="Supervisor tidak ditemukan")

    # Fetch team from external API
    token = get_system_token()
    employees = []
    if token:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        url = "https://hris-api.atibusinessgroup.com/api/app/overtime/request-data"
        try:
            res = requests.get(url, headers=headers, timeout=8)
            if res.status_code == 200:
                employees = res.json().get("employee", [])
        except Exception as e:
            print(f"[Sync Warning] Failed to fetch subordinates from API: {str(e)}")

    if employees:
        api_niks = {emp["nik"] for emp in employees if emp.get("nik")}
        for emp in employees:
            emp_nik = emp.get("nik")
            emp_name = emp.get("name")
            emp_id = emp.get("id")

            if not emp_nik:
                continue

            # Skip the supervisor themselves
            if emp_nik == spv.nik:
                continue

            sub = db.query(models.User).filter(models.User.nik == emp_nik).first()
            if sub:
                sub.supervisor_id = spv.id
                sub.employee_id = str(emp_id)
                sub.full_name = emp_name
                db.commit()
            else:
                temp_id = str(emp_id)
                id_exists = db.query(models.User).filter(models.User.id == temp_id).first()
                if id_exists:
                    temp_id = f"ext_{emp_id}"
                
                new_user = models.User(
                    id=temp_id,
                    nik=emp_nik,
                    employee_id=str(emp_id),
                    full_name=emp_name,
                    roles=["EMPLOYEE"],
                    has_subordinates=False,
                    is_active=True,
                    division_id=spv.division_id,
                    supervisor_id=spv.id,
                    jira_account_id=f"jira_user_{temp_id}",
                    gitlab_username=f"gitlab_user_{temp_id}"
                )
                db.add(new_user)
                db.commit()

        if "ROLE_ADMIN" not in spv.roles:
            db.query(models.User).filter(
                models.User.supervisor_id == spv.id,
                ~models.User.nik.in_(list(api_niks))
            ).update({"supervisor_id": None}, synchronize_session=False)
            db.commit()

    users = get_recursive_subordinates(db, supervisor_id)

    return [
        {
            "id": u.id,
            "nik": u.nik,
            "employeeId": u.employee_id,
            "fullName": u.full_name,
            "email": u.email,
            "roles": u.roles,
            "supervisor_id": u.supervisor_id,
            "hasSubordinates": u.has_subordinates
        } for u in users
    ]

@app.get("/api/v1/kpi/reports/sprint/{sprint_id}")
@cache(expire=60)
def get_sprint_report(sprint_id: str, supervisor_id: str, db: Session = Depends(get_db)):
    spv = db.query(models.User).filter(models.User.id == supervisor_id).first()
    if not spv:
        raise HTTPException(status_code=404, detail="User login tidak ditemukan")

    allowed_users = get_recursive_subordinates(db, supervisor_id)
    allowed_users.append(spv)

    allowed_user_ids = [u.id for u in allowed_users]

    scores = db.query(models.SprintKPIScore).filter(
        models.SprintKPIScore.sprint_id == sprint_id,
        models.SprintKPIScore.user_id.in_(allowed_user_ids)
    ).all()

    results = []
    for s in scores:
        u = next((x for x in allowed_users if x.id == s.user_id), None)
        if not u:
            continue
        raw_m = db.query(models.RawMetricsData).filter(
            models.RawMetricsData.user_id == s.user_id,
            models.RawMetricsData.sprint_id == sprint_id
        ).first()

        results.append({
            "user_id": s.user_id,
            "full_name": u.full_name,
            "nik": u.nik,
            "final_score": float(s.final_score),
            "breakdown": s.breakdown_details,
            "raw_metrics": raw_m.metrics_payload if raw_m else {}
        })

    return results

@app.get("/api/v1/kpi-rules")
def get_kpi_rules(division_id: str, group_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.KPIRule).filter(
        models.KPIRule.division_id == division_id,
        models.KPIRule.is_active == True
    )
    if group_id:
        query = query.filter(models.KPIRule.group_id == group_id)
    else:
        query = query.filter(models.KPIRule.group_id.is_(None))
        
    rule = query.first()

    if not rule:
        return []

    metrics = db.query(models.KPIRuleMetric).filter(
        models.KPIRuleMetric.kpi_rule_id == rule.id
    ).all()

    return {
        "rule_id": rule.id,
        "division_id": rule.division_id,
        "name": rule.name,
        "version": rule.version,
        "metrics": [
            {
                "metric_key": m.metric_key,
                "weight": float(m.weight),
                "calc_type": m.calc_type,
                "formula_expression": m.formula_expression,
                "variables": m.variables,
                "cap_score": float(m.cap_score)
            } for m in metrics
        ]
    }

@app.post("/api/v1/kpi-rules")
def create_or_update_kpi_rule(payload: KPIRuleInput, db: Session = Depends(get_db)):
    query = db.query(models.KPIRule).filter(
        models.KPIRule.division_id == payload.division_id
    )
    if payload.group_id:
        query = query.filter(models.KPIRule.group_id == payload.group_id)
    else:
        query = query.filter(models.KPIRule.group_id.is_(None))
        
    query.update({"is_active": False})

    latest = db.query(models.KPIRule).filter(
        models.KPIRule.division_id == payload.division_id
    )
    if payload.group_id:
        latest = latest.filter(models.KPIRule.group_id == payload.group_id)
    else:
        latest = latest.filter(models.KPIRule.group_id.is_(None))
        
    latest = latest.order_by(models.KPIRule.version.desc()).first()
    new_version = (latest.version + 1) if latest else 1

    new_rule = models.KPIRule(
        division_id=payload.division_id,
        group_id=payload.group_id,
        group_name=payload.group_name,
        name=payload.name,
        version=new_version,
        is_active=True
    )
    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)

    for m in payload.metrics:
        rule_metric = models.KPIRuleMetric(
            kpi_rule_id=new_rule.id,
            metric_key=m.metric_key,
            weight=m.weight,
            calc_type=m.calc_type,
            formula_expression=m.formula_expression,
            variables=m.variables,
            cap_score=m.cap_score
        )
        db.add(rule_metric)
    
    db.commit()
    return {"status": "success", "rule_id": new_rule.id, "version": new_version}

@app.post("/api/v1/kpi/evaluate-test")
def evaluate_test(payload: TestFormulaRequest):
    try:
        score = evaluate_kpi_formula(payload.formula, payload.context)
        return {"status": "success", "result": round(score, 2)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Integration Settings Endpoints (Opsi 2: Secure Decrypted Views)
@app.get("/api/v1/integrations")
def get_integrations(db: Session = Depends(get_db)):
    settings = db.query(models.IntegrationSetting).first()
    if not settings:
        return {
            "jira_url": "",
            "jira_email": "",
            "jira_token": None,
            "jira_board_id": "",
            "jira_sp_field": "customfield_10016",
            "gitlab_url": "https://gitlab.com",
            "gitlab_token": None
        }
    
    # Mask tokens in GET response to prevent leakage
    return {
        "jira_url": settings.jira_url or "",
        "jira_email": settings.jira_email or "",
        "jira_token": "••••••••••••••••" if settings.jira_token_encrypted else None,
        "jira_board_ids": settings.jira_board_ids or [],
        "default_jira_board_id": settings.default_jira_board_id or "",
        "jira_board_id": settings.default_jira_board_id or "",
        "jira_sp_field": settings.jira_sp_field or "customfield_10016",
        "gitlab_url": settings.gitlab_url or "https://gitlab.com",
        "gitlab_token": "••••••••••••••••" if settings.gitlab_token_encrypted else None
    }

@app.post("/api/v1/integrations")
def save_integrations(payload: IntegrationSettingInput, db: Session = Depends(get_db)):
    settings = db.query(models.IntegrationSetting).first()
    if not settings:
        settings = models.IntegrationSetting()
        db.add(settings)

    settings.jira_url = payload.jira_url
    settings.jira_email = payload.jira_email
    
    # Handle multiple boards
    if payload.jira_board_ids:
        settings.jira_board_ids = payload.jira_board_ids
    elif not settings.jira_board_ids:
        settings.jira_board_ids = []
    
    # Handle default board
    if payload.default_jira_board_id:
        settings.default_jira_board_id = payload.default_jira_board_id
    elif payload.jira_board_id:
        settings.default_jira_board_id = payload.jira_board_id
    
    settings.jira_sp_field = payload.jira_sp_field
    settings.gitlab_url = payload.gitlab_url

    # Only update tokens if provided (and not equal to masked string)
    if payload.jira_token and payload.jira_token != "••••••••••••••••":
        settings.jira_token_encrypted = encrypt_val(payload.jira_token)
        
    if payload.gitlab_token and payload.gitlab_token != "••••••••••••••••":
        settings.gitlab_token_encrypted = encrypt_val(payload.gitlab_token)

    db.commit()
    return {"status": "success", "message": "Integrasi berhasil diperbarui!"}

# ─────────────────────────────────────────────────────────────
# USER BOARD ASSIGNMENTS ENDPOINTS
# ─────────────────────────────────────────────────────────────

@app.get("/api/v1/boards")
def get_available_boards(db: Session = Depends(get_db)):
    """Get all available Jira boards from configured integration"""
    settings = db.query(models.IntegrationSetting).first()
    if not settings:
        return []
    
    try:
        from encrypt import decrypt_val
        token = decrypt_val(settings.jira_token_encrypted)
        jira_auth = (settings.jira_email, token)
        
        boards_url = f"{settings.jira_url}/rest/agile/1.0/board"
        response = requests.get(boards_url, auth=jira_auth, timeout=10)
        
        if response.status_code == 200:
            boards = response.json().get("values", [])
            return [
                {
                    "id": board.get("id"),
                    "name": board.get("name"),
                    "type": board.get("type"),
                    "location": board.get("location", {}).get("name", "Unknown")
                } for board in boards
            ]
        else:
            return []
    except Exception as e:
        print(f"Error fetching boards: {str(e)}")
        return []

@app.get("/api/v1/users/{user_id}/boards")
def get_user_board_assignments(user_id: str, db: Session = Depends(get_db)):
    """Get user's board assignments and their active sprint"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    
    settings = db.query(models.IntegrationSetting).first()
    if settings:
        from multi_board_sync import get_user_active_sprint
        active_sprint = get_user_active_sprint(db, user, settings)
    else:
        active_sprint = None
    
    return {
        "user_id": user.id,
        "full_name": user.full_name,
        "jira_board_ids": user.jira_board_ids or [],
        "current_active_board": user.current_active_board,
        "active_sprint": {
            "id": active_sprint.id,
            "sprint_name": active_sprint.sprint_name,
            "jira_sprint_id": active_sprint.jira_sprint_id,
            "jira_board_id": active_sprint.jira_board_id,
            "status": active_sprint.status
        } if active_sprint else None
    }

@app.post("/api/v1/users/{user_id}/boards")
def set_user_board_assignments(user_id: str, payload: UserBoardAssignmentInput, db: Session = Depends(get_db)):
    """Set user's board assignments"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    
    user.jira_board_ids = payload.jira_board_ids
    user.current_active_board = payload.current_active_board
    db.commit()
    
    return {"status": "success", "message": f"Board assignments untuk {user.full_name} berhasil diupdate"}

# ─────────────────────────────────────────────────────────────
# ATTENDANCE ENDPOINTS
# ─────────────────────────────────────────────────────────────

@app.get("/api/v1/attendance/summary")
def get_attendance_summary(sprint_id: str, supervisor_id: str = None, user_id: str = None, db: Session = Depends(get_db)):
    """Get attendance summary for users in a sprint."""
    sprint = db.query(models.Sprint).filter(models.Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint tidak ditemukan")
    
    # Determine which users to query
    if user_id:
        users = db.query(models.User).filter(models.User.id == user_id).all()
    elif supervisor_id:
        users = get_recursive_subordinates(db, supervisor_id)
    else:
        users = db.query(models.User).all()
    
    if not users:
        return []
    
    # Sync attendance (generates if not exists)
    att_results = sync_attendance_for_sprint(db, sprint, users)
    
    summaries = []
    for user in users:
        att_data = att_results.get(user.id, {})
        summaries.append({
            "user_id": user.id,
            "full_name": user.full_name,
            "nik": user.nik,
            "attendance_days": att_data.get("attendance_days", 0),
            "target_days": att_data.get("target_days", 0),
            "late_count": att_data.get("late_count", 0),
            "absent_count": att_data.get("absent_count", 0),
            "late_percentage": att_data.get("late_percentage", 0),
            "normal_percentage": att_data.get("normal_percentage", 100),
            "total_late_minutes": att_data.get("total_late_minutes", 0),
            "records": att_data.get("records", [])
        })
    
    return summaries

class ManualAttendanceInput(BaseModel):
    user_id: str
    sprint_id: str
    date: str
    clock_in: str = None
    clock_out: str = None
    status: str = "PRESENT"  # PRESENT, ABSENT, LATE, LEAVE

@app.post("/api/v1/attendance/manual")
def add_manual_attendance(payload: ManualAttendanceInput, db: Session = Depends(get_db)):
    """Add or update a manual attendance record."""
    user = db.query(models.User).filter(models.User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    
    # Check if record already exists
    existing = db.query(models.AttendanceRecord).filter(
        models.AttendanceRecord.user_id == payload.user_id,
        models.AttendanceRecord.sprint_id == payload.sprint_id,
        models.AttendanceRecord.date == payload.date
    ).first()
    
    # Calculate late status
    is_late = False
    late_minutes = 0
    if payload.clock_in and payload.status != "ABSENT":
        from sync_service import calculate_late_status
        late_info = calculate_late_status(payload.clock_in, "09:00:00")
        is_late = late_info["is_late"]
        late_minutes = late_info["late_minutes"]
    
    if existing:
        existing.clock_in = payload.clock_in
        existing.clock_out = payload.clock_out
        existing.status = "LATE" if is_late else payload.status
        existing.is_late = is_late
        existing.late_minutes = late_minutes
        existing.source = "MANUAL"
    else:
        new_record = models.AttendanceRecord(
            user_id=payload.user_id,
            sprint_id=payload.sprint_id,
            date=payload.date,
            clock_in=payload.clock_in,
            clock_out=payload.clock_out,
            scheduled_in="09:00:00",
            is_late=is_late,
            late_minutes=late_minutes,
            status="LATE" if is_late else payload.status,
            source="MANUAL"
        )
        db.add(new_record)
    
    db.commit()
    return {"status": "success", "message": "Attendance record saved"}

# ─────────────────────────────────────────────────────────────
# KPI CALCULATION (ENHANCED WITH ATTENDANCE)
# ─────────────────────────────────────────────────────────────

@app.post("/api/v1/sync/year/{year}")
async def sync_year(year: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    from sync_engine import create_sync_job, update_job_progress, mark_job_completed, mark_job_failed
    job_id = create_sync_job(db, None, "YEARLY_KPI_CALC")

    def run_calculation(jid):
        from fastapi_cache import FastAPICache
        from scheduler import sync_and_calculate_all_users_job
        from database import SessionLocal
        bg_db = SessionLocal()
        try:
            update_job_progress(bg_db, jid, 10, "RUNNING")
            sync_and_calculate_all_users_job(year)
            try:
                FastAPICache.clear()
            except Exception:
                pass
            mark_job_completed(bg_db, jid, {"message": "Sync completed successfully"})
        except Exception as e:
            print(f"Error in background calculation: {str(e)}")
            mark_job_failed(bg_db, jid, str(e))
        finally:
            bg_db.close()
            
    background_tasks.add_task(run_calculation, job_id)
    return {"status": "success", "message": f"Sinkronisasi tahun {year} berjalan di background", "job_id": job_id}

# ─────────────────────────────────────────────────────────────
# SYNC TRIGGER ENDPOINTS
# ─────────────────────────────────────────────────────────────

@app.get("/api/v1/sync/force-prod-fix")
async def force_prod_fix(background_tasks: BackgroundTasks):
    """
    Temporary endpoint to run the prod_sync_fix.py logic safely in the background
    """
    def run_prod_fix_bg():
        try:
            import prod_sync_fix
            prod_sync_fix.run_prod_sync()
        except Exception as e:
            print(f"Error in prod fix: {e}")
            
    background_tasks.add_task(run_prod_fix_bg)
    return {
        "status": "success", 
        "message": "Script sinkronisasi paksa (prod_sync_fix) sedang dijalankan di latar belakang. Silakan tunggu 1-2 menit lalu cek dashboard."
    }


@app.get("/api/v1/sync/status")
def get_sync_status(db: Session = Depends(get_db)):
    from sync_engine import get_active_sync_status
    return get_active_sync_status(db)

@app.get("/api/v1/jobs/{job_id}")
def get_job_status_endpoint(job_id: str, db: Session = Depends(get_db)):
    from sync_engine import get_job_status
    status = get_job_status(db, job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status

# ─────────────────────────────────────────────────────────────
# SYNC TRIGGER ENDPOINTS
# ─────────────────────────────────────────────────────────────

@app.post("/api/v1/sync/trigger")
def trigger_sync(background_tasks: BackgroundTasks):
    """Manually trigger both sprint and KPI calculation sync."""
    def run_full_sync():
        try:
            from scheduler import sync_sprints_job, sync_and_calculate_all_users_job
            from fastapi_cache import FastAPICache
            
            logger.info("Manual sync triggered")
            sync_sprints_job()
            sync_and_calculate_all_users_job()
            
            # Invalidate cache after sync completes
            try:
                FastAPICache.clear()
                logger.info("Cache invalidated after manual sync")
            except Exception as e:
                logger.warning(f"Failed to invalidate cache: {e}")
                
        except Exception as e:
            logger.error(f"Error in manual sync: {str(e)}")
    
    background_tasks.add_task(run_full_sync)
    return {"status": "success", "message": "Sync triggered in background"}

# ─────────────────────────────────────────────────────────────
# YEARLY KPI ENDPOINTS
# ─────────────────────────────────────────────────────────────

@app.get("/api/v1/kpi/yearly-performance")
def get_yearly_performance(year: int, user_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Get accumulated KPI data for a specific year (Jan 1 - Dec 31) for the current user.
    Uses company-wide relative scoring benchmark.
    """
    from_date_str = f"{year}-01-01"
    to_date_str = f"{year}-12-31"
    
    request = TimeRangeKPIRequest(from_date=from_date_str, to_date=to_date_str, user_ids=[user_id])
    kpi_data = get_time_range_kpi(request=request, user_id=user_id, db=db)
    
    if "users" in kpi_data:
        for u in kpi_data["users"]:
            if u["user_id"] == user_id:
                # Check if data is completely empty. If so, trigger a background sync.
                if u["summary"]["total_activities"] == 0 and u["summary"]["total_issues_completed"] == 0:
                    user = db.query(models.User).filter(models.User.id == user_id).first()
                    settings = db.query(models.IntegrationSetting).first()
                    if user and settings:
                        from_date = datetime.strptime(from_date_str, "%Y-%m-%d")
                        to_date = datetime.strptime(to_date_str, "%Y-%m-%d")
                        background_tasks.add_task(sync_user_comprehensive, db, user, settings, from_date, to_date)
                    # Tell frontend that data is syncing
                    u["is_syncing"] = True
                
                return {"status": "success", "data": u}
    
    return {"status": "success", "data": None, "message": "No data found for the year."}


@app.get("/api/v1/kpi/team-yearly")
def get_team_yearly_performance(year: int, user_id: str, db: Session = Depends(get_db)):
    """
    Get accumulated KPI data for a specific year (Jan 1 - Dec 31) for all subordinates.
    """
    current_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not (current_user.has_subordinates or "ROLE_ADMIN" in current_user.roles):
        raise HTTPException(status_code=403, detail="Not authorized to view team KPI")
        
    # Get recursive subordinates for the user
    users = get_recursive_subordinates(db, user_id)
    # Filter active users
    users = [u for u in users if u.is_active]
        
    target_user_ids = [u.id for u in users]
    
    from_date_str = f"{year}-01-01"
    to_date_str = f"{year}-12-31"
    
    request = TimeRangeKPIRequest(from_date=from_date_str, to_date=to_date_str, user_ids=target_user_ids)
    kpi_data = get_time_range_kpi(request=request, user_id=user_id, db=db)
    
    return {"status": "success", "data": kpi_data.get("users", [])}

# ─────────────────────────────────────────────────────────────
# TIME RANGE BASED KPI ENDPOINTS (NEW ARCHITECTURE)
# ─────────────────────────────────────────────────────────────

class TimeRangeKPIRequest(BaseModel):
    from_date: str  # YYYY-MM-DD
    to_date: str    # YYYY-MM-DD
    user_ids: List[str] = []  # Empty means current user only

@app.post("/api/v1/kpi/time-range")
def get_time_range_kpi(request: TimeRangeKPIRequest, user_id: str, db: Session = Depends(get_db)):
    """
    Get KPI data for users within a specific time range
    This follows the documentation's time-range based approach
    """
    
    try:
        from_date = datetime.strptime(request.from_date, "%Y-%m-%d")
        to_date = datetime.strptime(request.to_date, "%Y-%m-%d")
        
        # Determine which users to query
        target_user_ids = request.user_ids if request.user_ids else [user_id]
        
        # Verify user has permission to view other users' data
        current_user = db.query(models.User).filter(models.User.id == user_id).first()
        if not current_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if len(target_user_ids) > 1:
            # check role using index 0 as requested
            primary_role = current_user.roles[0] if current_user.roles else None
            is_authorized = current_user.has_subordinates or "ROLE_ADMIN" in current_user.roles or primary_role == "MANAGER"
            if not is_authorized:
                # Can only query own data unless supervisor, admin, or manager
                target_user_ids = [user_id]
        
        # === PASS 1: Calculate 5-Pillar Team Maxima per requested period ===
        req_year_pass1 = from_date.year
        all_active_users = db.query(models.User).filter(models.User.is_active == True).all()
        
        user_p1_metrics = {}
        from founder_engine import get_founder_credits_for_user
        from feature_analyzer import calculate_feature_weight
        
        for u_p1 in all_active_users:
            raw_sp_p1 = 0.0
            complexity_sp_p1 = 0.0
            issues_cnt_p1 = 0
            
            jira_id_p1 = db.query(models.EmployeeIdentity).filter(
                models.EmployeeIdentity.user_id == u_p1.id,
                models.EmployeeIdentity.source == 'jira'
            ).first()
            
            if jira_id_p1 and jira_id_p1.external_user_id:
                raw_j_p1 = db.query(models.RawJiraIssue).filter(
                    models.RawJiraIssue.assignee_account_id == jira_id_p1.external_user_id
                ).all()
                for ji in raw_j_p1:
                    r_dt_naive = None
                    if ji.resolved_date:
                        r_dt = ji.resolved_date
                        r_dt_naive = r_dt.replace(tzinfo=None) if hasattr(r_dt, 'replace') else r_dt
                    elif ji.raw_data and 'fields' in ji.raw_data:
                        fields_p1 = ji.raw_data['fields']
                        r_date_str = fields_p1.get('resolutiondate') or fields_p1.get('updated') or fields_p1.get('created')
                        if r_date_str:
                            try:
                                clean_date = r_date_str.split('.')[0]
                                if 'T' in clean_date:
                                    r_dt_naive = datetime.strptime(clean_date, "%Y-%m-%dT%H:%M:%S")
                                else:
                                    r_dt = datetime.fromisoformat(clean_date.replace('Z', '+00:00'))
                                    r_dt_naive = r_dt.replace(tzinfo=None)
                            except Exception:
                                pass
                    if not r_dt_naive and (ji.updated_date or ji.created_date):
                        r_dt = ji.updated_date or ji.created_date
                        r_dt_naive = r_dt.replace(tzinfo=None) if hasattr(r_dt, 'replace') else r_dt
                        
                    if r_dt_naive and from_date <= r_dt_naive <= to_date:
                        try:
                            status_lower = (ji.status or "").lower()
                            if status_lower in ["done", "resolved", "ready to release", "ready for uat", "uat (user)", "ready for qa", "in qa"]:
                                issues_cnt_p1 += 1
                                sp = float(ji.story_points or 0.0)
                                cw = calculate_feature_weight(ji.raw_data or {})
                                raw_sp_p1 += sp
                                complexity_sp_p1 += cw
                        except Exception:
                            pass
                            
            founder_p1 = get_founder_credits_for_user(u_p1.id, target_year=req_year_pass1)
            
            user_p1_metrics[u_p1.id] = {
                "raw_sp": raw_sp_p1,
                "complexity_sp": complexity_sp_p1,
                "issues_cnt": issues_cnt_p1,
                "founder_sp": founder_p1
            }
            
        max_raw_sp = max((m["raw_sp"] for m in user_p1_metrics.values()), default=1.0) or 1.0
        max_complexity_sp = max((m["complexity_sp"] for m in user_p1_metrics.values()), default=1.0) or 1.0
        max_issues_cnt = max((m["issues_cnt"] for m in user_p1_metrics.values()), default=1.0) or 1.0
        max_founder_sp = max((m["founder_sp"] for m in user_p1_metrics.values()), default=1.0) or 1.0
        global_max_sp = max_raw_sp
            
        logger.info(f"Calculated 5-pillar maxima: raw_sp={max_raw_sp}, complexity={max_complexity_sp}, issues={max_issues_cnt}, founder={max_founder_sp}")
        
        results = []
        
        for target_user_id in target_user_ids:
            user = db.query(models.User).filter(models.User.id == target_user_id).first()
            if not user:
                continue
            
            # Get daily KPI for the time range
            daily_kpis = db.query(models.KPIEmployeeDaily).filter(
                models.KPIEmployeeDaily.user_id == user.id,
                models.KPIEmployeeDaily.date >= from_date,
                models.KPIEmployeeDaily.date <= to_date
            ).order_by(models.KPIEmployeeDaily.date).all()
            
            # Check if daily KPIs are stale/incomplete — rebuild if so
            # We compare against AttendanceRecord count to detect staleness
            att_source_count = db.query(models.AttendanceRecord).filter(
                models.AttendanceRecord.user_id == user.id,
                models.AttendanceRecord.date >= from_date.date().isoformat(),
                models.AttendanceRecord.date <= to_date.date().isoformat()
            ).count()
            
            daily_kpi_with_att = sum(1 for d in daily_kpis if d.attendance_days > 0) if daily_kpis else 0
            needs_rebuild = (not daily_kpis) or (att_source_count > 0 and daily_kpi_with_att == 0)
            
            if needs_rebuild:
                # Attempt on-the-fly daily KPI aggregation for requested period
                try:
                    from comprehensive_sync import calculate_daily_aggregated_kpi
                    
                    # Collect all dates that have activities or attendance
                    from sqlalchemy import and_
                    rebuild_dates = set()
                    
                    act_dates = db.query(models.Activity.activity_date).filter(
                        and_(
                            models.Activity.user_id == user.id,
                            models.Activity.activity_date >= from_date,
                            models.Activity.activity_date <= to_date
                        )
                    ).distinct().all()
                    for r in act_dates:
                        if r[0]:
                            if isinstance(r[0], datetime):
                                rebuild_dates.add(r[0].date())
                            elif hasattr(r[0], 'year'):
                                rebuild_dates.add(r[0])
                    
                    att_dates = db.query(models.AttendanceRecord.date).filter(
                        and_(
                            models.AttendanceRecord.user_id == user.id,
                            models.AttendanceRecord.date >= from_date.date().isoformat(),
                            models.AttendanceRecord.date <= to_date.date().isoformat()
                        )
                    ).distinct().all()
                    for r in att_dates:
                        if r[0]:
                            if isinstance(r[0], str):
                                try:
                                    rebuild_dates.add(datetime.strptime(r[0][:10], "%Y-%m-%d").date())
                                except Exception:
                                    pass
                            elif isinstance(r[0], datetime):
                                rebuild_dates.add(r[0].date())
                            elif hasattr(r[0], 'year'):
                                rebuild_dates.add(r[0])
                    
                    logger.info(f"Rebuilding KPIEmployeeDaily for user {user.id}: {len(rebuild_dates)} dates found")
                    for d in sorted(rebuild_dates):
                        calculate_daily_aggregated_kpi(db, user, datetime.combine(d, datetime.min.time()))
                    
                    db.commit()

                    daily_kpis = db.query(models.KPIEmployeeDaily).filter(
                        models.KPIEmployeeDaily.user_id == user.id,
                        models.KPIEmployeeDaily.date >= from_date,
                        models.KPIEmployeeDaily.date <= to_date
                    ).order_by(models.KPIEmployeeDaily.date).all()
                except Exception as e:
                    logger.error(f"On-the-fly KPI aggregation error for user {user.id}: {e}")
                    db.rollback()
            
            if not daily_kpis:
                daily_kpis = []
            
            # ── SOURCE-OF-TRUTH: Query attendance directly from AttendanceRecord ──
            attendance_records = db.query(models.AttendanceRecord).filter(
                models.AttendanceRecord.user_id == user.id,
                models.AttendanceRecord.date >= from_date.date().isoformat(),
                models.AttendanceRecord.date <= to_date.date().isoformat()
            ).all()
            
            total_attendance_days = 0
            total_late_count = 0
            for att in attendance_records:
                if att.status in ["PRESENT", "LATE"]:
                    total_attendance_days += 1
                if att.is_late:
                    total_late_count += 1
            
            # Fallback: if no AttendanceRecord exists (e.g. 2025 historical data),
            # aggregate from KPIEmployeeDaily instead
            if not attendance_records and daily_kpis:
                unique_att_dates = set()
                for daily in daily_kpis:
                    date_key = daily.date.strftime('%Y-%m-%d') if hasattr(daily.date, 'strftime') else str(daily.date).split()[0]
                    if date_key not in unique_att_dates:
                        unique_att_dates.add(date_key)
                        total_attendance_days += daily.attendance_days
                        total_late_count += daily.late_count
            
            # ── SOURCE-OF-TRUTH: Query commits/MR from Activity table as fallback ──
            activities_in_range = db.query(models.Activity).filter(
                models.Activity.user_id == user.id,
                models.Activity.activity_date >= from_date,
                models.Activity.activity_date <= to_date
            ).all()
            
            direct_commits = sum(1 for a in activities_in_range if a.source == "gitlab" and a.activity_type == "commit")
            direct_mrs = sum(1 for a in activities_in_range if a.source == "gitlab" and a.activity_type in ["mr_merged", "merge_request"])
            
            # Aggregate from KPIEmployeeDaily for supplementary data
            day_count = len(daily_kpis)
            
            kpi_commits = sum(d.commit_count for d in daily_kpis)
            kpi_mrs = sum(d.mr_merged for d in daily_kpis)
            total_worklog_hours = sum(d.worklog_minutes / 60 for d in daily_kpis)
            
            # Use whichever source has more data
            total_commits = max(kpi_commits, direct_commits)
            total_mrs_merged = max(kpi_mrs, direct_mrs)
            
            unique_projects = set()
            unique_sprints = set()
            
            for daily in daily_kpis:
                if daily.project_id:
                    unique_projects.add(daily.project_id)
                if daily.sprint_id:
                    unique_sprints.add(daily.sprint_id)
            
            # Query raw Jira completed issues and raw Jira SP sum for the requested date range
            jira_ident = db.query(models.EmployeeIdentity).filter(
                models.EmployeeIdentity.user_id == user.id,
                models.EmployeeIdentity.source == 'jira'
            ).first()
            
            raw_jira_issues_count = 0
            raw_jira_sp_sum = 0.0
            complexity_sp_sum = 0.0
            completed_tasks_list = []
            from feature_analyzer import calculate_feature_weight, analyze_multi_factor
            
            if jira_ident and jira_ident.external_user_id:
                all_raw_jiras = db.query(models.RawJiraIssue).filter(
                    models.RawJiraIssue.assignee_account_id == jira_ident.external_user_id
                ).all()
                
                for ji in all_raw_jiras:
                    r_dt_naive = None
                    if ji.resolved_date:
                        r_dt = ji.resolved_date
                        r_dt_naive = r_dt.replace(tzinfo=None) if hasattr(r_dt, 'replace') else r_dt
                    elif ji.raw_data and 'fields' in ji.raw_data:
                        fields_p2 = ji.raw_data['fields']
                        r_date_str = fields_p2.get('resolutiondate') or fields_p2.get('updated') or fields_p2.get('created')
                        if r_date_str:
                            try:
                                clean_date = r_date_str.split('.')[0]
                                if 'T' in clean_date:
                                    r_dt_naive = datetime.strptime(clean_date, "%Y-%m-%dT%H:%M:%S")
                                else:
                                    r_dt = datetime.fromisoformat(clean_date.replace('Z', '+00:00'))
                                    r_dt_naive = r_dt.replace(tzinfo=None)
                            except Exception:
                                pass
                    if not r_dt_naive and (ji.updated_date or ji.created_date):
                        r_dt = ji.updated_date or ji.created_date
                        r_dt_naive = r_dt.replace(tzinfo=None) if hasattr(r_dt, 'replace') else r_dt
                        
                    if r_dt_naive and from_date <= r_dt_naive <= to_date:
                        try:
                            status_lower = (ji.status or "").lower()
                            if status_lower in ["done", "resolved", "ready to release", "ready for uat", "uat (user)", "ready for qa", "in qa"]:
                                raw_jira_issues_count += 1
                                sp = float(ji.story_points or 0.0)
                                cw = calculate_feature_weight(ji.raw_data or {})
                                raw_jira_sp_sum += sp
                                complexity_sp_sum += cw
                                
                                mf_res = analyze_multi_factor(ji.raw_data or {})
                                completed_tasks_list.append({
                                    "key": ji.issue_key,
                                    "summary": ji.raw_data.get('fields', {}).get('summary', ji.issue_key),
                                    "description": str(ji.raw_data.get('fields', {}).get('description', '')) if ji.raw_data.get('fields', {}).get('description') else '',
                                    "status": ji.status or "Done",
                                    "resolved_date": r_dt_naive.strftime("%Y-%m-%d") if r_dt_naive else None,
                                    "points": mf_res["kpi_points"],
                                    "complexity": mf_res["complexity"],
                                    "impact": mf_res["impact"],
                                    "scope": mf_res["scope"],
                                    "risk": mf_res["risk"],
                                    "ownership": mf_res["ownership"]
                                })
                        except Exception:
                            pass

            total_issues_completed = raw_jira_issues_count

            # Incorporate Founder Architecture Attribution Credit for the requested year
            req_year = from_date.year
            from founder_engine import get_founder_credits_for_user, get_founder_projects_info
            founder_sp_credit = get_founder_credits_for_user(user.id, target_year=req_year)
            
            # Single source of truth for total_story_points
            total_story_points = raw_jira_sp_sum + founder_sp_credit
            founder_projects = get_founder_projects_info(user.id, target_year=req_year)
            
            # Also fetch all project_ids from Activity table to get all GitLab and Jira projects
            act_projects = db.query(models.Activity.project_id).filter(
                models.Activity.user_id == user.id,
                models.Activity.activity_date >= from_date,
                models.Activity.activity_date <= to_date,
                models.Activity.project_id.isnot(None)
            ).distinct().all()
            for ap in act_projects:
                if ap[0]:
                    unique_projects.add(ap[0])
            
            from yearly_kpi_engine import YearlyKPIEngine
            
            target_days = YearlyKPIEngine.calculate_working_days(from_date, to_date)
            late_pct = (total_late_count / target_days * 100) if target_days > 0 else 0
            
            aggregated_metrics = {
                "gitlab_commits": total_commits,
                "gitlab_mr": total_mrs_merged,
                "gitlab_mr_merged": total_mrs_merged,
                "jira_sp": total_story_points,
                "raw_jira_sp": raw_jira_sp_sum,
                "complexity_sp": complexity_sp_sum,
                "jira_issues_completed": total_issues_completed,
                "worklog_hours": total_worklog_hours,
                "attendance_days": total_attendance_days,
                "attendance": total_attendance_days,
                "late_count": total_late_count,
                "late_percentage": late_pct,
                "founder_sp_credit": founder_sp_credit,
                "max_raw_sp": max_raw_sp,
                "max_complexity_sp": max_complexity_sp,
                "max_issues_cnt": max_issues_cnt,
                "max_founder_sp": max_founder_sp
            }
            
            engine_result = YearlyKPIEngine.calculate_yearly_kpi(
                db=db,
                user_id=user.id,
                start_date=from_date,
                end_date=to_date,
                aggregated_metrics=aggregated_metrics,
                team_max_sp=global_max_sp
            )
            
            # Extract scores from engine result
            avg_delivery = 0
            avg_engineering = 0
            avg_effort = 0
            avg_quality = 0
            avg_overall = 0
            
            if "final_score" in engine_result:
                avg_overall = engine_result["final_score"]
                for b in engine_result.get("breakdown", []):
                    cat = b.get("category", "").upper()
                    if cat == "DELIVERY":
                        avg_delivery += b.get("weighted_score", 0)
                    elif cat == "ENGINEERING":
                        avg_engineering += b.get("weighted_score", 0)
                    elif cat == "EFFORT":
                        avg_effort += b.get("weighted_score", 0)
                    elif cat == "QUALITY":
                        avg_quality += b.get("weighted_score", 0)
            
            # Get project and sprint details
            project_names = []
            if unique_projects:
                projects = db.query(models.Project).filter(models.Project.id.in_(list(unique_projects))).all()
                project_names = [{"id": p.id, "name": p.project_name} for p in projects]
            
            sprint_names = []
            if unique_sprints:
                sprints = db.query(models.Sprint).filter(models.Sprint.id.in_(list(unique_sprints))).all()
                sprint_names = [{"id": s.id, "name": s.sprint_name, "status": s.status} for s in sprints]
            
            results.append({
                "user_id": user.id,
                "full_name": user.full_name,
                "nik": user.nik,
                "email": user.email,
                "completed_tasks": completed_tasks_list,
                "period": {
                    "from_date": from_date.strftime("%Y-%m-%d"),
                    "to_date": to_date.strftime("%Y-%m-%d"),
                    "day_count": max(day_count, total_attendance_days)
                },
                "summary": {
                    "projects_count": len(unique_projects),
                    "sprints_count": len(unique_sprints),
                    "total_activities": max(sum(d.raw_activity_count for d in daily_kpis), len(activities_in_range)),
                    "total_commits": total_commits,
                    "total_mrs_merged": total_mrs_merged,
                    "total_worklog_hours": round(total_worklog_hours, 2),
                    "total_issues_completed": total_issues_completed,
                    "total_story_points": round(total_story_points, 2),
                    "total_attendance_days": total_attendance_days,
                    "total_late_count": total_late_count,
                    "founder_architecture_credit": founder_sp_credit,
                    "founder_projects": founder_projects
                },
                "projects": project_names,
                "sprints": sprint_names,
                "kpi_scores": {
                    "delivery": round(avg_delivery, 2),
                    "engineering": round(avg_engineering, 2),
                    "effort": round(avg_effort, 2),
                    "quality": round(avg_quality, 2),
                    "overall": round(avg_overall, 2),
                    "details": engine_result.get("breakdown", [])
                },
                "final_score": round(avg_overall, 2),
                "daily_breakdown": [
                    {
                        "date": daily.date.strftime("%Y-%m-%d"),
                        "overall_score": round(daily.overall_score, 2),
                        "commit_count": daily.commit_count,
                        "mr_merged": daily.mr_merged,
                        "worklog_hours": round(daily.worklog_minutes / 60, 2),
                        "issues_completed": daily.issue_completed
                    }
                    for daily in daily_kpis
                ]
            })
        
        return {
            "period": {
                "from_date": from_date.strftime("%Y-%m-%d"),
                "to_date": to_date.strftime("%Y-%m-%d")
            },
            "users": results,
            "total_users": len(results)
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ComprehensiveSyncRequest(BaseModel):
    from_date: str  # YYYY-MM-DD
    to_date: str    # YYYY-MM-DD
    user_ids: List[str] = []  # Empty means all active users

@app.get("/api/v1/admin/clean-kpi-daily")
def clean_kpi_daily_2026(db: Session = Depends(get_db)):
    """Temporary endpoint to clean corrupted KPIEmployeeDaily for 2026"""
    from datetime import date
    try:
        deleted = db.query(models.KPIEmployeeDaily).filter(models.KPIEmployeeDaily.date >= date(2026, 1, 1)).delete(synchronize_session=False)
        db.commit()
        return {"status": "success", "deleted": deleted, "message": "Corrupted 2026 data cleared"}
    except Exception as e:
        db.rollback()
        import traceback
        return {"status": "error", "error": str(e), "trace": traceback.format_exc()}

@app.post("/api/v1/sync/comprehensive")
def trigger_comprehensive_sync(request: ComprehensiveSyncRequest, background_tasks: BackgroundTasks, user_id: str, db: Session = Depends(get_db)):
    """
    Trigger comprehensive sync following the documentation's architecture
    This syncs activities from GitLab and Jira for time range and aggregates KPI
    """
    
    # Verify user has permission to trigger sync
    current_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not current_user or not ("ROLE_ADMIN" in current_user.roles):
        raise HTTPException(status_code=403, detail="Only admins can trigger comprehensive sync")
    
    try:
        from_date = datetime.strptime(request.from_date, "%Y-%m-%d")
        to_date = datetime.strptime(request.to_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Determine which users to sync
    if request.user_ids:
        target_user_ids = request.user_ids
    else:
        # Sync all active IT division users
        it_division = db.query(models.Division).filter(models.Division.code == "IT").first()
        if not it_division:
            target_user_ids = []
        else:
            users = db.query(models.User).filter(
                models.User.division_id == it_division.id,
                models.User.is_active == True
            ).all()
            target_user_ids = [u.id for u in users]
    
    settings = db.query(models.IntegrationSetting).first()
    
    from sync_engine import create_sync_job, update_job_progress, mark_job_completed, mark_job_failed
    job_id = create_sync_job(db, user_id, "COMPREHENSIVE_SYNC")
    
    def run_comprehensive_sync(j_id, t_user_ids, frm_dt, t_dt):
        from database import SessionLocal
        _db = SessionLocal()
        try:
            update_job_progress(_db, j_id, 10, "RUNNING")
            try:
                from fastapi_cache import FastAPICache
                
                logger.info(f"Starting comprehensive sync for {len(t_user_ids)} users from {frm_dt} to {t_dt}")
                
                results = []
                for idx, u_id in enumerate(t_user_ids):
                    u = _db.query(models.User).filter(models.User.id == u_id).first()
                    if not u:
                        continue
                    
                    # Run comprehensive sync for this user
                    from comprehensive_sync import sync_user_comprehensive, calculate_daily_aggregated_kpi
                    result = sync_user_comprehensive(_db, u, settings, frm_dt, t_dt)
                    results.append(result)
                    
                    # Update progress roughly
                    prog = 10 + int(40 * (idx + 1) / len(t_user_ids))
                    update_job_progress(_db, j_id, prog, "RUNNING")
                
                # Calculate daily aggregated KPI for all synced data
                logger.info("Calculating daily aggregated KPI...")
                
                current_date = frm_dt
                days_total = (t_dt - frm_dt).days + 1
                days_done = 0
                
                while current_date <= t_dt:
                    for u_id in t_user_ids:
                        u = _db.query(models.User).filter(models.User.id == u_id).first()
                        if u:
                            from comprehensive_sync import calculate_daily_aggregated_kpi
                            calculate_daily_aggregated_kpi(_db, u, current_date)
                    
                    current_date += timedelta(days=1)
                    days_done += 1
                    
                    # Update progress roughly
                    prog = 50 + int(40 * days_done / days_total)
                    update_job_progress(_db, j_id, prog, "RUNNING")
                
                # Invalidate cache after comprehensive sync
                try:
                    FastAPICache.clear()
                    logger.info("Cache invalidated after comprehensive sync")
                except Exception as e:
                    logger.warning(f"Failed to invalidate cache: {e}")
                
                logger.info(f"Comprehensive sync completed for {len(results)} users")
                mark_job_completed(_db, j_id, {"users_synced": len(results)})
                
            except Exception as e:
                logger.error(f"Error in comprehensive sync: {str(e)}")
                mark_job_failed(_db, j_id, str(e))
        finally:
            _db.close()
    
    background_tasks.add_task(run_comprehensive_sync, job_id, target_user_ids, from_date, to_date)
    
    return {
        "status": "success",
        "message": f"Comprehensive sync triggered for {len(target_user_ids)} users",
        "time_range": {
            "from_date": from_date.strftime("%Y-%m-%d"),
            "to_date": to_date.strftime("%Y-%m-%d")
        },
        "users_count": len(target_user_ids),
        "job_id": job_id
    }

@app.get("/api/v1/users/{user_id}/identities")
def get_user_identities(user_id: str, db: Session = Depends(get_db)):
    """Get user's external identities (GitLab, Jira, etc.)"""
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    identities = db.query(models.EmployeeIdentity).filter(
        models.EmployeeIdentity.user_id == user_id
    ).all()
    
    identity_list = []
    for identity in identities:
        identity_list.append({
            "source": identity.source,
            "external_user_id": identity.external_user_id,
            "username": identity.username,
            "email": identity.email,
            "is_verified": identity.is_verified,
            "full_name": identity.full_name
        })
    
    return {
        "user_id": user_id,
        "full_name": user.full_name,
        "identities": identity_list
    }

@app.get("/api/v1/kpi/activities")
def get_user_activities(user_id: str, from_date: str, to_date: str, db: Session = Depends(get_db)):
    """Get user's activity timeline for time range"""
    
    try:
        start_date = datetime.strptime(from_date, "%Y-%m-%d")
        end_date = datetime.strptime(to_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Verify user permission
    current_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get activities
    activities = db.query(models.Activity).filter(
        and_(
            models.Activity.user_id == user_id,
            models.Activity.activity_date >= start_date,
            models.Activity.activity_date <= end_date
        )
    ).order_by(models.Activity.activity_at).all()
    
    activity_list = []
    
    for activity in activities:
        activity_data = {
            "id": activity.id,
            "activity_type": activity.activity_type,
            "source": activity.source,
            "activity_date": activity.activity_date.isoformat(),
            "activity_at": activity.activity_at.isoformat(),
            "reference_id": activity.reference_id,
            "metadata": activity.metadata
        }
        
        # Add project info if available
        if activity.project_id:
            project = db.query(models.Project).filter(models.Project.id == activity.project_id).first()
            if project:
                activity_data["project"] = {
                    "id": project.id,
                    "name": project.project_name,
                    "source": project.source
                }
        
        # Add sprint info if available
        if activity.sprint_id:
            sprint = db.query(models.Sprint).filter(models.Sprint.id == activity.sprint_id).first()
            if sprint:
                activity_data["sprint"] = {
                    "id": sprint.id,
                    "sprint_name": sprint.sprint_name,
                    "status": sprint.status
                }
        
        activity_list.append(activity_data)
    
    return {
        "user_id": user_id,
        "full_name": current_user.full_name,
        "time_range": {
            "from_date": from_date,
            "to_date": to_date
        },
        "total_activities": len(activity_list),
        "activities": activity_list
    }

# ─── DB Maintenance & Cleanup ───────────────────────────────────────────────────

@app.get("/api/v1/health")
def health_check():
    """Simple health check that doesn't need DB - useful when DB is down"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/api/v1/db/stats")
def db_stats(db: Session = Depends(get_db)):
    """Get table row counts to diagnose disk usage"""
    try:
        stats = {}
        tables = [
            "raw_jira_issues", "activities", "raw_jira_issue_history",
            "raw_jira_worklogs", "attendance_records", "kpi_employee_daily",
            "sprint_kpi_scores", "raw_metrics_data", "sync_jobs"
        ]
        for t in tables:
            try:
                result = db.execute(text(f"SELECT COUNT(*) FROM {t}"))
                stats[t] = result.scalar()
            except Exception:
                stats[t] = "table not found"
        return {"status": "ok", "table_counts": stats}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.post("/api/v1/db/cleanup")
def db_cleanup(db: Session = Depends(get_db)):
    """
    Emergency cleanup: remove duplicate raw_jira_issues, 
    truncate old sync_jobs, and reclaim disk space.
    """
    results = {}
    
    # 1. Remove duplicate raw_jira_issues (keep the newest by created_at)
    try:
        dup_count = db.execute(text("""
            DELETE FROM raw_jira_issues 
            WHERE id NOT IN (
                SELECT DISTINCT ON (issue_key) id 
                FROM raw_jira_issues 
                ORDER BY issue_key, created_at DESC
            )
        """))
        db.commit()
        results["raw_jira_issues_duplicates_removed"] = dup_count.rowcount
    except Exception as e:
        db.rollback()
        # Try SQLite-compatible version
        try:
            dup_count = db.execute(text("""
                DELETE FROM raw_jira_issues 
                WHERE rowid NOT IN (
                    SELECT MIN(rowid) FROM raw_jira_issues GROUP BY issue_key
                )
            """))
            db.commit()
            results["raw_jira_issues_duplicates_removed"] = dup_count.rowcount
        except Exception as e2:
            db.rollback()
            results["raw_jira_issues_cleanup"] = f"skipped: {str(e2)}"
    
    # 2. Remove duplicate activities (keep newest per user+reference_id+source)
    try:
        dup_act = db.execute(text("""
            DELETE FROM activities 
            WHERE id NOT IN (
                SELECT DISTINCT ON (user_id, source, reference_id) id 
                FROM activities 
                ORDER BY user_id, source, reference_id, created_at DESC
            )
        """))
        db.commit()
        results["activities_duplicates_removed"] = dup_act.rowcount
    except Exception as e:
        db.rollback()
        try:
            dup_act = db.execute(text("""
                DELETE FROM activities 
                WHERE rowid NOT IN (
                    SELECT MIN(rowid) FROM activities 
                    GROUP BY user_id, source, activity_type, reference_id
                )
            """))
            db.commit()
            results["activities_duplicates_removed"] = dup_act.rowcount
        except Exception as e2:
            db.rollback()
            results["activities_cleanup"] = f"skipped: {str(e2)}"
    
    # 3. Cleanup old completed sync_jobs (keep last 50)
    try:
        old_jobs = db.execute(text("""
            DELETE FROM sync_jobs 
            WHERE id NOT IN (
                SELECT id FROM sync_jobs ORDER BY created_at DESC LIMIT 50
            )
        """))
        db.commit()
        results["old_sync_jobs_removed"] = old_jobs.rowcount
    except Exception as e:
        db.rollback()
        results["sync_jobs_cleanup"] = f"skipped: {str(e)}"
    
    # 4. Cleanup old raw_jira_issue_history (keep last 30 days)
    try:
        old_hist = db.execute(text("""
            DELETE FROM raw_jira_issue_history 
            WHERE created_at < NOW() - INTERVAL '30 days'
        """))
        db.commit()
        results["old_history_removed"] = old_hist.rowcount
    except Exception as e:
        db.rollback()
        results["history_cleanup"] = f"skipped: {str(e)}"
    
    # 5. Try VACUUM to reclaim disk space (Postgres only, won't work in transaction)
    try:
        db.commit()  # ensure no open transaction
        # Need a separate connection for VACUUM
        from database import engine
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text("VACUUM FULL"))
        results["vacuum"] = "completed"
    except Exception as e:
        results["vacuum"] = f"skipped: {str(e)}"
    
    # Get updated stats
    try:
        final_stats = {}
        for t in ["raw_jira_issues", "activities", "sync_jobs"]:
            try:
                result = db.execute(text(f"SELECT COUNT(*) FROM {t}"))
                final_stats[t] = result.scalar()
            except Exception:
                pass
        results["final_counts"] = final_stats
    except Exception:
        pass
    
    return {"status": "cleanup_completed", "results": results}

@app.post("/api/v1/db/truncate-raw-data")
def truncate_raw_data(db: Session = Depends(get_db)):
    """
    NUCLEAR OPTION: Truncate raw_jira_issues, raw_jira_issue_history, 
    and raw_jira_worklogs to free maximum disk space.
    The data will be re-synced on next Jira sync.
    """
    results = {}
    
    for table in ["raw_jira_issue_history", "raw_jira_worklogs", "raw_jira_issues", "activities", "sync_jobs"]:
        try:
            # We can't use COUNT if the DB is fully locked/hanging, so just TRUNCATE directly
            db.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
            db.commit()
            results[table] = {"truncated": True}
        except Exception as e:
            db.rollback()
            results[table] = {"error": str(e)}
    
    # VACUUM to reclaim space
    try:
        from database import engine
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text("VACUUM FULL"))
        results["vacuum"] = "completed"
    except Exception as e:
        results["vacuum"] = f"skipped: {str(e)}"
    
    return {"status": "truncated", "results": results}
