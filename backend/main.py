import requests
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, Response
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

# Cache for expensive company-wide maxima computation (PASS 1).
# Keyed by year; invalidated after sync operations. TTL prevents stale data.
_company_maxima_cache = {}
_COMPANY_MAXIMA_TTL = 1800  # 30 minutes

# Background jobs tracking for team yearly KPI
TEAM_YEARLY_JOBS = {}

from database import engine, get_db
import models
from engine import DynamicKPIEngine, evaluate_kpi_formula
from encrypt import encrypt_val, decrypt_val
import os
import time
from contextlib import asynccontextmanager
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache
from scheduler import init_scheduler
from sync_service import sync_attendance_for_sprint
from multi_board_sync import sync_all_boards_sprints, get_user_active_sprint
from comprehensive_sync import sync_user_comprehensive, calculate_daily_aggregated_kpi

def sync_subordinates_for_supervisor(db, supervisor, token):
    """
    Fetch subordinates of a supervisor from HRIS and assign the supervisor's
    division/group to each employee. Idempotent — safe to call multiple times.
    Returns the number of employees processed.
    """
    if not supervisor or not token:
        return 0

    hdr = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    url = "https://hris-api.atibusinessgroup.com/api/app/overtime/request-data"
    try:
        res = requests.get(url, headers=hdr, timeout=8)
        if res.status_code != 200:
            print(f"[Sync] Failed to fetch subordinates for {supervisor.id}: HTTP {res.status_code}")
            return 0
        employees = res.json().get("employee", [])
    except Exception as e:
        print(f"[Sync Warning] Failed to fetch subordinates for {supervisor.id}: {str(e)}")
        return 0

    supervisor_division_id = supervisor.division_id
    supervisor_group_id = supervisor.group_id
    supervisor_group_name = supervisor.group_name

    processed = 0
    for emp in employees:
        emp_nik = emp.get("nik")
        emp_name = emp.get("name")
        emp_id = emp.get("id")

        if not emp_nik:
            continue
        if emp_nik == supervisor.nik:
            continue

        sub = db.query(models.User).filter(models.User.nik == emp_nik).first()
        if sub:
            sub.supervisor_id = supervisor.id
            sub.employee_id = str(emp_id)
            sub.full_name = emp_name
            if supervisor_division_id:
                sub.division_id = supervisor_division_id
            if supervisor_group_id:
                sub.group_id = supervisor_group_id
                sub.group_name = supervisor_group_name
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
                division_id=supervisor_division_id,
                group_id=supervisor_group_id,
                group_name=supervisor_group_name,
                supervisor_id=supervisor.id,
                jira_account_id=f"jira_user_{temp_id}",
                gitlab_username=f"gitlab_user_{temp_id}"
            )
            db.add(new_sub)
            db.commit()
        processed += 1

    # Remove supervisor links for subordinates no longer returned by HRIS
    if "ROLE_ADMIN" not in (supervisor.roles or []):
        api_niks = {emp["nik"] for emp in employees if emp.get("nik")}
        db.query(models.User).filter(
            models.User.supervisor_id == supervisor.id,
            ~models.User.nik.in_(list(api_niks))
        ).update({"supervisor_id": None}, synchronize_session=False)
        db.commit()

    return processed

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables and seed data if empty
    from database import engine, SessionLocal
    import models
    from seed import seed_data
    from sqlalchemy import text
    
    print("Starting KPI Dashboard backend...")
    
    try:
        print("Starting database initialization...")
        
        # Create tables first
        print("Creating database tables...")
        models.Base.metadata.create_all(bind=engine)
        print("Database tables created successfully")

        # Auto-migrate columns added to existing tables (create_all only adds new tables).
        # Uses SQLAlchemy Inspector so it works on both SQLite and PostgreSQL.
        try:
            from sqlalchemy import inspect as sa_inspect
            _insp = sa_inspect(engine)

            def _existing_cols(table_name):
                try:
                    return {c["name"] for c in _insp.get_columns(table_name)}
                except Exception:
                    return set()

            ri_cols = _existing_cols("raw_jira_issues")
            if ri_cols and "complexity_score" not in ri_cols:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE raw_jira_issues ADD COLUMN complexity_score FLOAT"))
                print("Migrated: raw_jira_issues.complexity_score")
            if ri_cols and "complexity_detail" not in ri_cols:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE raw_jira_issues ADD COLUMN complexity_detail JSON"))
                print("Migrated: raw_jira_issues.complexity_detail")

            cm_cols = _existing_cols("company_maxima")
            if cm_cols and "group_id" not in cm_cols:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE company_maxima ADD COLUMN group_id VARCHAR(50)"))
                print("Migrated: company_maxima.group_id")
            if cm_cols and "division_id" not in cm_cols:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE company_maxima ADD COLUMN division_id VARCHAR(50)"))
                print("Migrated: company_maxima.division_id")

            uym_cols = _existing_cols("user_yearly_metrics")
            if uym_cols and "last_processed_date" not in uym_cols:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE user_yearly_metrics ADD COLUMN last_processed_date TIMESTAMP"))
                print("Migrated: user_yearly_metrics.last_processed_date")

            # Performance indexes for KPI calculation hot paths
            with engine.begin() as conn:
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_kpi_daily_user_date ON kpi_employee_daily (user_id, date)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_activities_user_date ON activities (user_id, activity_date)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_attendance_user_date ON attendance_records (user_id, date)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_emp_identity_user_source ON employee_identity (user_id, source)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_raw_jira_assignee_resolved ON raw_jira_issues (assignee_account_id, resolved_date)"))
            print("Performance indexes ensured")

            # Unique constraints (dedup leftovers) + extra query-path indexes.
            # Single source of truth shared with fix_production_db.py.
            from db_maintenance import ensure_constraints_and_indexes
            ensure_constraints_and_indexes(engine)
        except Exception as mig_e:
            print(f"Warning: auto-migration skipped: {mig_e}")

        db = SessionLocal()
        
        # Check if database is empty and needs seeding
        user_count = db.query(models.User).count()
        print(f"Current users count: {user_count}")
        
        if user_count == 0:
            print("Database is empty, running seed script...")
            seed_data()
            print("Seed data populated successfully")
        else:
            print(f"Database already contains {user_count} users")
        
        # Ensure default divisions exist
        it_division = db.query(models.Division).filter(models.Division.code == "IT").first()
        if not it_division:
            print("Creating default IT division...")
            it_div = models.Division(code="IT", name="IT & Engineering", description="Information Technology Division")
            db.add(it_div)
            db.commit()
            print("Default IT division created")
        else:
            print("Default IT division already exists")
            
        # Ensure integration settings exist
        integration_settings = db.query(models.IntegrationSetting).first()
        if not integration_settings:
            print("Creating default integration settings...")
            default_settings = models.IntegrationSetting(
                jira_url="",
                jira_email="", 
                jira_token_encrypted="",
                jira_board_ids=[],
                default_jira_board_id="",
                jira_sp_field="customfield_10016",
                gitlab_url="https://gitlab.com",
                gitlab_token_encrypted=""
            )
            db.add(default_settings)
            db.commit()
            print("Default integration settings created")
        else:
            print("Integration settings already exist")
        
        db.close()
        print("Database initialization complete")

        FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")
        print("Cache initialized")
        
        # init_scheduler() is removed for standalone worker approach
        print("Application ready to accept requests")
        yield
        
    except Exception as e:
        print(f"CRITICAL ERROR during startup: {e}")
        import traceback
        traceback.print_exc()
        # Still try to start even if DB init fails
        FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")
        yield

app = FastAPI(title="Dynamic KPI Dashboard API", lifespan=lifespan)

# Health check endpoint for Railway
@app.get("/health")
def health_check():
    """Health check endpoint for Railway monitoring"""
    try:
        from database import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }, 503

# Database diagnostics endpoint
@app.get("/api/v1/db/diagnostics")
def db_diagnostics():
    """Database diagnostics endpoint for debugging production issues"""
    from database import engine
    from models import User, Division, Sprint, KPIRule, IntegrationSetting
    from sqlalchemy import inspect
    
    diagnostics = {
        "timestamp": datetime.now().isoformat(),
        "database_url_type": "postgresql" if "postgresql" in str(engine.url) else "sqlite",
        "status": "unknown"
    }
    
    try:
        with engine.connect() as conn:
            # Test basic connection
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
            
            # Get table info
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            diagnostics["tables"] = tables
            
            # Check data counts
            from database import SessionLocal
            db = SessionLocal()
            try:
                diagnostics["counts"] = {
                    "users": db.query(User).count(),
                    "divisions": db.query(Division).count(),
                    "sprints": db.query(Sprint).count(),
                    "kpi_rules": db.query(KPIRule).count(),
                    "integration_settings": db.query(IntegrationSetting).count()
                }
                
                # Check critical data
                it_division = db.query(Division).filter(Division.code == "IT").first()
                diagnostics["it_division_exists"] = it_division is not None
                
                integration_settings = db.query(IntegrationSetting).first()
                diagnostics["integration_settings_exist"] = integration_settings is not None
                
                # Determine overall status
                if (diagnostics["counts"]["divisions"] > 0 and 
                    diagnostics["integration_settings_exist"]):
                    diagnostics["status"] = "healthy"
                else:
                    diagnostics["status"] = "needs_setup"
                    
            finally:
                db.close()
                
        return diagnostics, 200
        
    except Exception as e:
        diagnostics["status"] = "error"
        diagnostics["error"] = str(e)
        return diagnostics, 500


@app.get("/api/v1/db/index-diagnostics")
def db_index_diagnostics():
    """List expected vs actual indexes (verifies the AUTO_INDEX maintenance)."""
    from database import engine
    from sqlalchemy import inspect
    from db_maintenance import UNIQUE_INDEXES, EXTRA_INDEXES

    inspector = inspect(engine)
    actual = {}
    for table in inspector.get_table_names():
        actual[table] = [i.get("name") for i in inspector.get_indexes(table)]

    expected = {name: f"{table}({', '.join(cols)})"
                for name, table, cols in (UNIQUE_INDEXES + EXTRA_INDEXES)}
    missing = {name: spec for name, spec in expected.items()
               if name not in {idx for lst in actual.values() for idx in lst}}

    return {
        "status": "ok" if not missing else "missing_indexes",
        "expected": expected,
        "actual": actual,
        "missing": missing,
    }


@app.get("/api/v1/kpi/formula-errors")
def kpi_formula_errors(year: int = None, limit: int = 100, db: Session = Depends(get_db)):
    """List daily rows whose kpi_breakdown recorded formula evaluation errors.

    Lets operators find mis-configured formula rules instead of users silently
    scoring 0.0 because of a typo in the Configurator matrix.
    """
    from datetime import datetime as _dt
    if not year:
        year = _dt.now().year
    start = _dt(year, 1, 1)
    end = _dt(year, 12, 31, 23, 59, 59)

    rows = (
        db.query(models.KPIEmployeeDaily)
        .filter(
            models.KPIEmployeeDaily.date >= start,
            models.KPIEmployeeDaily.date <= end,
        )
        .order_by(models.KPIEmployeeDaily.date.desc())
        .limit(limit)
        .all()
    )
    matches = []
    for r in rows:
        breakdown = r.kpi_breakdown or {}
        if isinstance(breakdown, str):
            try:
                import json as _json
                breakdown = _json.loads(breakdown)
            except Exception:
                breakdown = {}
        errs = breakdown.get("formula_errors") if isinstance(breakdown, dict) else None
        if errs:
            matches.append({
                "user_id": r.user_id,
                "date": r.date.strftime("%Y-%m-%d") if r.date else None,
                "errors": errs,
            })
    return {"year": year, "found": len(matches), "errors": matches[:limit]}

# Force database initialization endpoint
@app.post("/api/v1/db/initialize")
def force_db_initialize():
    """Force database initialization - useful for production setup"""
    from database import engine, SessionLocal
    import models
    from models import Division, IntegrationSetting
    from sqlalchemy import text
    
    try:
        # Create tables
        models.Base.metadata.create_all(bind=engine)
        
        # Ensure divisions exist
        db = SessionLocal()
        try:
            if not db.query(Division).filter(Division.code == "IT").first():
                it_div = Division(code="IT", name="IT & Engineering", description="Information Technology Division")
                db.add(it_div)
                db.commit()
                
            # Ensure integration settings exist  
            if not db.query(IntegrationSetting).first():
                default_settings = IntegrationSetting(
                    jira_url="",
                    jira_email="", 
                    jira_token_encrypted="",
                    jira_board_ids=[],
                    default_jira_board_id="",
                    jira_sp_field="customfield_10016",
                    gitlab_url="https://gitlab.com",
                    gitlab_token_encrypted=""
                )
                db.add(default_settings)
                db.commit()
                
            return {
                "status": "success",
                "message": "Database initialized successfully",
                "timestamp": datetime.now().isoformat()
            }
        finally:
            db.close()
            
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }, 500

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

# NEW: AI INDICATOR CREATOR MODELS
class AIFormulaRequest(BaseModel):
    user_id: str
    user_name: str
    user_role: str
    has_subordinates: bool
    division_id: str
    division_name: str
    division_code: str
    group_id: Optional[str] = None
    group_name: Optional[str] = None
    creation_scope: str = "personal"
    indicator_description: str

# Helper: Recursive Subordinates Lookup
def get_recursive_subordinates(db: Session, supervisor_id: str) -> List[models.User]:
    return _recursive_subordinates(db, supervisor_id, set())


def _recursive_subordinates(db: Session, supervisor_id: str, visited: set) -> List[models.User]:
    if supervisor_id in visited:
        return []
    visited = set(visited)
    visited.add(supervisor_id)
    direct_subs = db.query(models.User).filter(models.User.supervisor_id == supervisor_id).all()
    all_subs = list(direct_subs)
    for sub in direct_subs:
        all_subs.extend(_recursive_subordinates(db, sub.id, visited))
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
    
    # Handle supervisor link — purely from HRIS, no special-casing
    supervisor_id = None
    direct_spv = user_data.get("directSpv")
    if direct_spv and direct_spv.get("id"):
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
            supervisor = _db.query(models.User).filter(models.User.id == supervisor_user_id).first()
            if supervisor:
                sync_subordinates_for_supervisor(_db, supervisor, token)
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
def get_subordinates_list(supervisor_id: str, db: Session = Depends(get_db)):
    spv = db.query(models.User).filter(models.User.id == supervisor_id).first()
    if not spv:
        raise HTTPException(status_code=404, detail="Supervisor tidak ditemukan")

    # Use the supervisor's OWN token (stored at their login). Never fall back to a
    # shared/system account — every manager must see only their own team.
    stored = _supervisor_token_store.get(supervisor_id)
    token = None
    if stored and stored.get("token") and stored.get("expires_at", datetime.min) > datetime.now():
        token = stored["token"]

    if token:
        sync_subordinates_for_supervisor(db, spv, token)

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

# NEW: AI INDICATOR CREATOR ENDPOINTS
@app.get("/api/v1/ai/division-context")
def get_ai_division_context(division_id: str, user_id: str, db: Session = Depends(get_db)):
    """Get division context for AI-powered indicator creation"""
    try:
        # Get user information
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get division information
        division = db.query(models.Division).filter(models.Division.id == division_id).first()
        if not division:
            raise HTTPException(status_code=404, detail="Division not found")
        
        # Import division variables registry
        from division_variables import (
            get_division_variables,
            get_division_example_prompts,
            get_division_common_targets,
            get_all_divisions
        )
        
        # Get user's permission level
        user_role = user.roles[0] if user.roles else "EMPLOYEE"
        
        # Get division-specific data
        division_variables = get_division_variables(division.code)
        example_prompts = get_division_example_prompts(division.code)
        common_targets = get_division_common_targets(division.code)
        
        # Determine creation scope based on user role
        if "ROLE_ADMIN" in user.roles:
            creation_scopes = ["division", "group", "personal"]
        elif "MANAGER" in user.roles or user.has_subordinates:
            creation_scopes = ["group", "personal"]
        else:
            creation_scopes = ["personal"]
        
        return {
            "status": "success",
            "user_context": {
                "user_id": user.id,
                "user_name": user.full_name,
                "user_role": user_role,
                "has_subordinates": user.has_subordinates,
                "division_id": user.division_id,
                "group_id": user.group_id,
                "group_name": user.group_name,
                "creation_scopes": creation_scopes
            },
            "division_context": {
                "division_id": division.id,
                "division_name": division.name,
                "division_code": division.code,
                "variables": division_variables,
                "example_prompts": example_prompts,
                "common_targets": common_targets
            },
            "available_divisions": get_all_divisions()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting AI division context: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.post("/api/v1/ai/generate-formula")
async def ai_generate_formula(request: AIFormulaRequest, db: Session = Depends(get_db)):
    """Generate KPI formula using AI based on natural language description"""
    try:
        # Validate user exists
        user = db.query(models.User).filter(models.User.id == request.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Validate user permissions
        user_role = user.roles[0] if user.roles else "EMPLOYEE"
        if user_role == "EMPLOYEE":
            raise HTTPException(status_code=403, detail="Employees cannot create KPI indicators")
        
        # Validate division access
        if request.division_id != user.division_id and "ROLE_ADMIN" not in user.roles:
            raise HTTPException(status_code=403, detail="Cannot create indicators for other divisions")
        
        # Validate group access if group specified
        if request.group_id and request.group_id != user.group_id and "ROLE_ADMIN" not in user.roles:
            raise HTTPException(status_code=403, detail="Cannot create indicators for other groups")
        
        # Import AI formula generator
        from ai_formula_generator import AIFeatureScorer
        from ai_formula_generator import AIFormulaRequest as AIRequestModel
        
        # Create AI request
        ai_request = AIRequestModel(
            user_id=request.user_id,
            user_name=request.user_name,
            user_role=request.user_role,
            has_subordinates=request.has_subordinates,
            division_id=request.division_id,
            division_name=request.division_name,
            division_code=request.division_code,
            group_id=request.group_id,
            group_name=request.group_name,
            creation_scope=request.creation_scope,
            indicator_description=request.indicator_description
        )
        
        # Generate formula
        scorer = AIFeatureScorer()
        response = scorer.generate_formula(ai_request)
        
        # Add division-specific suggestions if AI fails
        if response.status == "error":
            from division_variables import get_division_example_prompts
            example_prompts = get_division_example_prompts(request.division_code)
            response.error = f"{response.error}. Try these examples: {', '.join(example_prompts[:2])}"
        
        return response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating AI formula: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to generate formula. Please try again or use manual formula creation."
        }

@app.post("/api/v1/ai/validate-permission")
def validate_indicator_creation_permission(user_id: str, scope: str, division_id: str, group_id: str = None, db: Session = Depends(get_db)):
    """Validate if user has permission to create indicators for given scope"""
    try:
        # Get user information
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Determine user permission level
        user_role = user.roles[0] if user.roles else "EMPLOYEE"
        
        # Check basic access
        if user_role == "EMPLOYEE":
            return {
                "status": "denied",
                "reason": "Employees cannot create KPI indicators",
                "suggestion": "Contact your manager for indicator changes"
            }
        
        # Check scope permissions
        if scope == "division":
            if "ROLE_ADMIN" not in user.roles:
                return {
                    "status": "denied",
                    "reason": "Only admins can create division-wide indicators",
                    "suggestion": "Create group-specific indicators instead"
                }
        
        if scope == "group":
            if group_id and group_id != user.group_id and "ROLE_ADMIN" not in user.roles:
                return {
                    "status": "denied",
                    "reason": "Cannot create indicators for other groups",
                    "suggestion": "Create indicators for your own group"
                }
        
        return {
            "status": "allowed",
            "user_role": user_role,
            "scope": scope,
            "division_access": division_id == user.division_id or "ROLE_ADMIN" in user.roles,
            "group_access": not group_id or group_id == user.group_id or "ROLE_ADMIN" in user.roles
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating permissions: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

# Enhanced debugging endpoint for checking employee calculations

@app.get("/api/v1/kpi/user-calculation-details")
def get_user_calculation_details(user_id: str, year: int, db: Session = Depends(get_db)):
    """Get detailed calculation breakdown for a user for debugging"""
    try:
        from_date = datetime(year, 1, 1)
        to_date = datetime(year, 12, 31)
        
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get rules for user
        rule = db.query(models.KPIRule).filter(
            models.KPIRule.division_id == user.division_id,
            models.KPIRule.group_id == user.group_id,
            models.KPIRule.is_active == True
        ).first()
        
        if not rule:
            rule = db.query(models.KPIRule).filter(
                models.KPIRule.division_id == user.division_id,
                models.KPIRule.group_id.is_(None),
                models.KPIRule.is_active == True
            ).first()
        
        if not rule:
            return {"error": "No active KPI rule found for user"}
        
        metrics = db.query(models.KPIRuleMetric).filter(
            models.KPIRuleMetric.kpi_rule_id == rule.id
        ).all()
        
        # Get actual metrics for user for this year
        from yearly_kpi_engine import YearlyKPIEngine, METRIC_RAW_KEY_MAP, _resolve_formula_raw_value
        
        working_days = YearlyKPIEngine.calculate_working_days(from_date, to_date)
        
        # Get user's actual metrics from database
        user_metrics = {}
        
        # Get daily KPI data
        daily_kpis = db.query(models.KPIEmployeeDaily).filter(
            models.KPIEmployeeDaily.user_id == user.id,
            models.KPIEmployeeDaily.date >= from_date,
            models.KPIEmployeeDaily.date <= to_date
        ).all()
        
        # Aggregate metrics
        user_metrics["attendance_days"] = sum(d.attendance_days for d in daily_kpis)
        user_metrics["target_days"] = working_days
        user_metrics["late_percentage"] = (sum(d.late_count for d in daily_kpis) / working_days * 100) if working_days > 0 else 0
        
        # Get Jira data
        jira_ident = db.query(models.EmployeeIdentity).filter(
            models.EmployeeIdentity.user_id == user.id,
            models.EmployeeIdentity.source == 'jira'
        ).first()
        
        if jira_ident and jira_ident.external_user_id:
            raw_jira_issues = db.query(models.RawJiraIssue).filter(
                models.RawJiraIssue.assignee_account_id == jira_ident.external_user_id
            ).all()

            from feature_analyzer import stored_feature_weight

            raw_jira_sp = 0.0
            complexity_sp = 0.0
            issues_completed = 0
            
            for ji in raw_jira_issues:
                # Extract date and check if within range
                r_dt_naive = None
                if ji.resolved_date:
                    r_dt = ji.resolved_date
                    r_dt_naive = r_dt.replace(tzinfo=None) if hasattr(r_dt, 'replace') else r_dt
                elif ji.raw_data and 'fields' in ji.raw_data:
                    fields = ji.raw_data['fields']
                    r_date_str = fields.get('resolutiondate') or fields.get('updated') or fields.get('created')
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
                
                if r_dt_naive and from_date <= r_dt_naive <= to_date:
                    status_lower = (ji.status or "").lower()
                    if status_lower in ["done", "resolved", "ready to release", "ready for uat", "uat (user)", "ready for qa", "in qa"]:
                        issues_completed += 1
                        sp = float(ji.story_points or 0.0)
                        cw = stored_feature_weight(ji)
                        raw_jira_sp += sp
                        complexity_sp += cw
            
            user_metrics["raw_jira_sp"] = raw_jira_sp
            user_metrics["jira_sp"] = raw_jira_sp
            user_metrics["complexity_sp"] = complexity_sp
            user_metrics["jira_issues_completed"] = issues_completed
            
            # Get founder credits
            from founder_engine import get_founder_credits_for_user
            user_metrics["founder_sp_credit"] = get_founder_credits_for_user(user.id, year)
            
            # Get company maxima for relative scoring (scoped to the user's group)
            from_date = datetime(year, 1, 1)
            to_date = datetime(year, 12, 31, 23, 59, 59)
            cmax = _get_company_maxima(db, from_date, to_date, group_id=user.group_id)
            max_raw_sp = cmax["max_raw_sp"]
            max_complexity_sp = cmax["max_complexity_sp"]
            max_issues_cnt = cmax["max_issues_cnt"]
            max_founder_sp = cmax["max_founder_sp"]
            
            user_metrics["max_raw_sp"] = max_raw_sp
            user_metrics["max_complexity_sp"] = max_complexity_sp
            user_metrics["max_issues_cnt"] = max_issues_cnt
            user_metrics["max_founder_sp"] = max_founder_sp
        
        # Calculate each metric with detailed breakdown
        breakdown_details = []
        for m_def in metrics:
            try:
                # Build eval context
                eval_context = dict(user_metrics)
                
                # Add variables from rule (actual metrics take precedence)
                try:
                    if m_def.variables:
                        from engine import merge_rule_variables
                        eval_context = merge_rule_variables(eval_context, m_def.variables)
                except Exception as e:
                    print(f"Error parsing variables for {m_def.metric_key}: {e}")
                
                # Calculate score
                from engine import evaluate_kpi_formula
                score = evaluate_kpi_formula(m_def.formula_expression, eval_context)
                capped_score = min(max(score, 0.0), float(m_def.cap_score))
                weighted_score = capped_score * float(m_def.weight)

                raw_key = METRIC_RAW_KEY_MAP.get(m_def.metric_key, m_def.metric_key)
                if raw_key in user_metrics:
                    actual_val = user_metrics.get(raw_key, user_metrics.get(m_def.metric_key, 0.0))
                else:
                    # AI-generated formula metric: resolve the raw measure behind the formula
                    # (e.g. jira_sp) so the dashboard "Nilai Raw" column shows real data.
                    actual_val = _resolve_formula_raw_value(m_def.formula_expression, user_metrics, eval_context)

                breakdown_details.append({
                    "metric_key": m_def.metric_key,
                    "formula": m_def.formula_expression,
                    "formula_used": m_def.formula_expression,
                    "variables": eval_context,
                    "variables_used": eval_context,
                    "actual_value": round(actual_val, 2),
                    "raw_score": round(score, 2),
                    "calculated_score": round(capped_score, 2),
                    "capped_score": round(capped_score, 2),
                    "weight": float(m_def.weight),
                    "weighted_score": round(weighted_score, 2),
                    "category": m_def.category or "ENGINEERING"
                })
            except Exception as e:
                breakdown_details.append({
                    "metric_key": m_def.metric_key,
                    "error": str(e),
                    "raw_score": 0,
                    "capped_score": 0,
                    "weighted_score": 0,
                    "weight": float(m_def.weight)
                })
        
        total_score = sum(b["weighted_score"] for b in breakdown_details)
        
        return {
            "user_id": user.id,
            "full_name": user.full_name,
            "year": year,
            "rule_name": rule.name,
            "total_score": round(total_score, 2),
            "working_days": working_days,
            "user_metrics": user_metrics,
            "breakdown": breakdown_details
        }
        
    except Exception as e:
        return {"error": str(e)}, 500

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
            _company_maxima_cache.clear()
            mark_job_completed(bg_db, jid, {"message": "Sync completed successfully"})
        except Exception as e:
            print(f"Error in background calculation: {str(e)}")
            try:
                bg_db.rollback()
            except Exception:
                pass
            _safe_mark_job_failed(bg_db, jid, str(e))
        finally:
            try:
                bg_db.rollback()
            except Exception:
                pass
            bg_db.close()
            
    background_tasks.add_task(run_calculation, job_id)
    return {"status": "success", "message": f"Sinkronisasi tahun {year} berjalan di background", "job_id": job_id}

@app.post("/api/v1/sync/data")
async def sync_data_only(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Sync data from Jira/GitLab into local DB only (no KPI calculation)."""
    from sync_engine import create_sync_job, update_job_progress, mark_job_completed, mark_job_failed, mark_stale_jobs_failed
    mark_stale_jobs_failed(db, "DATA_SYNC_ONLY")
    job_id = create_sync_job(db, None, "DATA_SYNC_ONLY")

    def run_sync(jid):
        from scheduler import sync_data_only_job
        from database import SessionLocal
        bg_db = SessionLocal()
        try:
            update_job_progress(bg_db, jid, 10, "RUNNING")
            result = sync_data_only_job()
            try:
                _company_maxima_cache.clear()
            except Exception:
                pass
            mark_job_completed(bg_db, jid, result or {"message": "Sync data completed"})
        except Exception as e:
            print(f"Error in background data sync: {str(e)}")
            try:
                bg_db.rollback()
            except Exception:
                pass
            _safe_mark_job_failed(bg_db, jid, str(e))
        finally:
            try:
                bg_db.rollback()
            except Exception:
                pass
            bg_db.close()

    background_tasks.add_task(run_sync, job_id)
    return {"status": "success", "message": "Sync data dari Jira/GitLab berjalan di background", "job_id": job_id}

def _safe_mark_job_failed(db, job_id, error):
    """Mark a job FAILED even when the session is broken/poisoned.

    A DB network error leaves the session with an invalid transaction, so the
    failure-marking query itself raises PendingRollbackError. Here we reset the
    session (rollback) before retrying and swallow the error so a poisoned
    session can never turn a background failure into an unhandled ASGI 500.
    """
    try:
        db.rollback()
    except Exception:
        pass
    try:
        from sync_engine import mark_job_failed
        mark_job_failed(db, job_id, error)
    except Exception as e:
        print(f"Failed to mark job {job_id} as failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass

@app.post("/api/v1/kpi/calculate/{year}")
async def calculate_kpi_only(year: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db), force: bool = False):
    """Calculate KPI using local DB data only (no external sync).

    By default only dates that are not already calculated are processed
    (incremental). Pass ?force=true to recalculate the whole year.
    """
    from sync_engine import create_sync_job, update_job_progress, mark_job_completed, mark_job_failed, mark_stale_jobs_failed, cancel_running_jobs
    mark_stale_jobs_failed(db, "KPI_CALC_ONLY")
    cancel_running_jobs(db, "KPI_CALC_ONLY")
    job_id = create_sync_job(db, None, "KPI_CALC_ONLY")

    def run_calc(jid):
        from scheduler import calculate_kpi_only_job
        from database import SessionLocal
        bg_db = SessionLocal()
        try:
            update_job_progress(bg_db, jid, 10, "RUNNING")
            def _progress_cb(pct):
                update_job_progress(bg_db, jid, int(pct), "RUNNING")
            result = calculate_kpi_only_job(year, job_id=jid, progress_cb=_progress_cb, force=force)
            try:
                _company_maxima_cache.clear()
            except Exception:
                pass
            status = (result or {}).get("status", "error")
            if status == "cancelled":
                # Job row was already marked FAILED by cancel_running_jobs;
                # do not resurrect it as COMPLETED.
                return
            if status == "error":
                _safe_mark_job_failed(bg_db, jid, (result or {}).get("message", "Kalkulasi KPI gagal"))
                return
            mark_job_completed(bg_db, jid, result or {"message": "KPI calculation completed"})
        except Exception as e:
            print(f"Error in background KPI calculation: {str(e)}")
            # The session may be left with an invalid transaction after a DB
            # network error. Roll back BEFORE reusing it, otherwise the failure
            # marking itself raises PendingRollbackError and the job stays
            # RUNNING forever (frontend polls a 200 OK that never changes).
            try:
                bg_db.rollback()
            except Exception:
                pass
            _safe_mark_job_failed(bg_db, jid, str(e))
        finally:
            try:
                bg_db.rollback()
            except Exception:
                pass
            bg_db.close()

    background_tasks.add_task(run_calc, job_id)
    return {"status": "success", "message": f"Kalkulasi KPI tahun {year} dari data lokal berjalan di background", "job_id": job_id}

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

class RescoreRequest(BaseModel):
    year: Optional[int] = None
    user_id: Optional[str] = None
    force: bool = False

@app.post("/api/v1/kpi/rescore")
def rescore_features(payload: RescoreRequest, background_tasks: BackgroundTasks):
    """Re-score stored Jira issues with the configured FeatureScorer (rules or LLM)
    and refresh the precomputed maxima/metrics. Runs in the background."""
    def _run_rescore():
        from database import SessionLocal, engine as _engine
        from locks import AppLock
        from feature_analyzer import FeatureScorer, resolve_feature_config, stored_feature_weight
        # A rescore both re-writes complexity scores and re-runs the precompute
        # (company maxima + daily aggregates), so it must not overlap a running
        # KPI calc on another worker/instance.
        _lock = AppLock(_engine, "KPI_CALC")
        if not _lock.try_acquire():
            logger.warning("Rescore skipped: another KPI calc/rescore holds the DB lock")
            return
        bg_db = SessionLocal()
        try:
            cfg = resolve_feature_config(bg_db)
            scorer = FeatureScorer(config=cfg)
            target_year = payload.year or datetime.now().year

            query = bg_db.query(models.RawJiraIssue)
            if payload.user_id:
                jira_ident = bg_db.query(models.EmployeeIdentity).filter(
                    models.EmployeeIdentity.user_id == payload.user_id,
                    models.EmployeeIdentity.source == 'jira'
                ).first()
                if not jira_ident or not jira_ident.external_user_id:
                    return
                query = query.filter(models.RawJiraIssue.assignee_account_id == jira_ident.external_user_id)
            issues = query.all()

            updated = 0
            for ji in issues:
                if not payload.force and ji.complexity_score is not None:
                    continue
                res = scorer.score(ji.raw_data or {})
                ji.complexity_score = float(res["kpi_points"])
                ji.complexity_detail = {
                    "technical_complexity": res["technical_complexity"],
                    "business_impact": res["business_impact"],
                    "system_scope": res["system_scope"],
                    "delivery_risk": res["delivery_risk"],
                    "ownership_level": res["ownership_level"],
                    "total_score": res["total_score"],
                    "kpi_points": float(res["kpi_points"]),
                    "score_type": res.get("score_type", "rules"),
                    "model": res.get("model"),
                    "prompt_version": res.get("prompt_version"),
                }
                updated += 1
                if updated % 20 == 0:
                    bg_db.commit()
            bg_db.commit()
            logger.info(f"Rescore completed: {updated} issues scored ({scorer.mode} mode)")

            # Refresh precomputed aggregates for the target year (full recompute,
            # because backfilled complexity values change old dates too).
            try:
                from precompute_metrics import compute_all_year_metrics
                compute_all_year_metrics(bg_db, target_year, force=True)
            except Exception as e:
                logger.error(f"Precompute after rescore failed: {e}")

            try:
                from fastapi_cache import FastAPICache
                FastAPICache.clear()
            except Exception:
                pass
            _company_maxima_cache.clear()
        except Exception as e:
            logger.error(f"Rescore failed: {e}")
            bg_db.rollback()
        finally:
            bg_db.close()
            try:
                _lock.release()
            except Exception:
                pass

    background_tasks.add_task(_run_rescore)
    return {"status": "success", "message": "Re-scoring dijalankan di background", "mode": "llm" if os.getenv("ZAI_API_KEY") else "rules"}

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
                _company_maxima_cache.clear()
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
@cache(expire=300)
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


def _run_team_yearly_kpi_job(db: Session, request: 'TimeRangeKPIRequest', user_id: str, job_key: str):
    import traceback
    try:
        kpi_data = get_time_range_kpi(request=request, user_id=user_id, db=db)
        TEAM_YEARLY_JOBS[job_key] = {"status": "success", "data": kpi_data.get("users", []), "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Error in team yearly background job: {e}")
        logger.error(traceback.format_exc())
        TEAM_YEARLY_JOBS[job_key] = {"status": "error", "data": [], "timestamp": datetime.now().isoformat()}


@app.get("/api/v1/kpi/team-yearly")
def get_team_yearly_performance(
    year: int, 
    user_id: str, 
    background_tasks: BackgroundTasks,
    response: Response,
    direct_only: bool = False, 
    db: Session = Depends(get_db)
):
    """
    Get accumulated KPI data for a specific year (Jan 1 - Dec 31) for all subordinates.

    By default returns the full recursive tree below the user. Pass ``direct_only=true``
    to limit the result to the user's direct reports only.
    """
    current_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not (current_user.has_subordinates or "ROLE_ADMIN" in current_user.roles):
        raise HTTPException(status_code=403, detail="Not authorized to view team KPI")
        
    # Get recursive subordinates for the user (or direct reports only)
    if direct_only:
        users = db.query(models.User).filter(
            models.User.supervisor_id == user_id,
            models.User.is_active == True
        ).all()
    else:
        users = get_recursive_subordinates(db, user_id)
        users = [u for u in users if u.is_active]
        
    target_user_ids = [u.id for u in users]
    
    from_date_str = f"{year}-01-01"
    to_date_str = f"{year}-12-31"
    
    job_key = f"{user_id}_{year}_{direct_only}"
    
    if job_key in TEAM_YEARLY_JOBS:
        job = TEAM_YEARLY_JOBS[job_key]
        
        # Check if job is older than 5 minutes
        is_stale = False
        if "timestamp" in job:
            try:
                job_time = datetime.fromisoformat(job["timestamp"])
                if (datetime.now() - job_time).total_seconds() > 300:
                    is_stale = True
            except ValueError:
                pass
                
        if is_stale and job["status"] != "processing":
            del TEAM_YEARLY_JOBS[job_key]
        else:
            if job["status"] == "processing":
                response.status_code = 202
                return {"status": "processing", "message": "Sedang menghitung data KPI tim..."}
            elif job["status"] == "success":
                data = job["data"]
                return {"status": "success", "data": data}
            elif job["status"] == "error":
                del TEAM_YEARLY_JOBS[job_key]
                return {"status": "error", "message": "Gagal menghitung KPI tim"}
            
    request = TimeRangeKPIRequest(from_date=from_date_str, to_date=to_date_str, user_ids=target_user_ids)
    
    # Start job
    TEAM_YEARLY_JOBS[job_key] = {"status": "processing", "data": None, "timestamp": datetime.now().isoformat()}
    background_tasks.add_task(_run_team_yearly_kpi_job, db, request, user_id, job_key)
    
    response.status_code = 202
    return {"status": "processing", "message": "Sedang memulai perhitungan KPI tim..."}

# ─────────────────────────────────────────────────────────────
# TIME RANGE BASED KPI ENDPOINTS (NEW ARCHITECTURE)
# ─────────────────────────────────────────────────────────────

def _compute_company_maxima(db: Session, from_date: datetime, to_date: datetime, users=None) -> Dict[str, float]:
    """
    Calculate 5-pillar company maxima (raw SP, complexity SP, issues, founder credits)
    for the given period by scanning the raw Jira data. When `users` is provided the
    benchmark is scoped to that group's indicator matrix; otherwise it is company-wide.
    Used only as a fallback when the precomputed CompanyMaxima row is missing.
    """
    req_year = from_date.year
    if users is None:
        users = db.query(models.User).filter(models.User.is_active == True).all()

    from founder_engine import get_founder_credits_for_user
    from feature_analyzer import stored_feature_weight

    user_metrics = {}
    for u in users:
        raw_sp = 0.0
        complexity_sp = 0.0
        issues_cnt = 0

        jira_ident = db.query(models.EmployeeIdentity).filter(
            models.EmployeeIdentity.user_id == u.id,
            models.EmployeeIdentity.source == 'jira'
        ).first()

        if jira_ident and jira_ident.external_user_id:
            raw_issues = db.query(models.RawJiraIssue).filter(
                models.RawJiraIssue.assignee_account_id == jira_ident.external_user_id
            ).all()
            for ji in raw_issues:
                r_dt_naive = None
                if ji.resolved_date:
                    r_dt = ji.resolved_date
                    r_dt_naive = r_dt.replace(tzinfo=None) if hasattr(r_dt, 'replace') else r_dt
                elif ji.raw_data and 'fields' in ji.raw_data:
                    fields = ji.raw_data['fields']
                    r_date_str = fields.get('resolutiondate') or fields.get('updated') or fields.get('created')
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
                            issues_cnt += 1
                            sp = float(ji.story_points or 0.0)
                            cw = stored_feature_weight(ji)
                            raw_sp += sp
                            complexity_sp += cw
                    except Exception:
                        pass

        founder = get_founder_credits_for_user(u.id, target_year=req_year)

        user_metrics[u.id] = {
            "raw_sp": raw_sp,
            "complexity_sp": complexity_sp,
            "issues_cnt": issues_cnt,
            "founder_sp": founder
        }

    maxima = {
        "max_raw_sp": max((m["raw_sp"] for m in user_metrics.values()), default=1.0) or 1.0,
        "max_complexity_sp": max((m["complexity_sp"] for m in user_metrics.values()), default=1.0) or 1.0,
        "max_issues_cnt": max((m["issues_cnt"] for m in user_metrics.values()), default=1.0) or 1.0,
        "max_founder_sp": max((m["founder_sp"] for m in user_metrics.values()), default=1.0) or 1.0,
    }
    logger.info(
        f"Calculated 5-pillar maxima: raw_sp={maxima['max_raw_sp']}, "
        f"complexity={maxima['max_complexity_sp']}, issues={maxima['max_issues_cnt']}, "
        f"founder={maxima['max_founder_sp']}"
    )
    return maxima


def _get_company_maxima(db: Session, from_date: datetime, to_date: datetime, group_id: Optional[str] = None) -> Dict[str, float]:
    """Read persisted company maxima at the given scope (fast DB lookup),
    falling back to a scan. group_id=None -> company-wide benchmark; a group_id
    -> that group's own indicator-matrix benchmark.

    The precompute job (scheduler / sync completion) keeps CompanyMaxima fresh,
    so the expensive scan is only used as a safety net on cold data.
    """
    year = from_date.year
    cache_key = f"{year}:{group_id or 'GLOBAL'}"
    now = time.time()
    hit = _company_maxima_cache.get(cache_key)
    if hit and now - hit[0] < _COMPANY_MAXIMA_TTL:
        return hit[1]

    try:
        from precompute_metrics import get_company_maxima
        maxima = get_company_maxima(db, year, group_id=group_id)
        if maxima:
            return maxima
    except Exception as e:
        logger.warning(f"CompanyMaxima lookup failed, falling back to scan: {e}")

    scope_users = None
    if group_id:
        scope_users = db.query(models.User).filter(
            models.User.is_active == True,
            models.User.group_id == group_id
        ).all()
    maxima = _compute_company_maxima(db, from_date, to_date, users=scope_users)
    _company_maxima_cache[cache_key] = (now, maxima)
    return maxima


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
                
        # === FAST FAIL CHECK ===
        # If there are NO attendance records AND no activities in this year globally for these users,
        # skip calculation to prevent long loading times when year is empty.
        # This will just return empty stats.
        fast_check_att = db.query(models.AttendanceRecord).filter(
            models.AttendanceRecord.date >= from_date.date().isoformat(),
            models.AttendanceRecord.date <= to_date.date().isoformat()
        ).first()
        fast_check_act = db.query(models.Activity).filter(
            models.Activity.activity_date >= from_date,
            models.Activity.activity_date <= to_date
        ).first()
        
        if not fast_check_att and not fast_check_act:
            logger.info("Fast-fail triggered: No data found for the requested period. Returning empty KPIs.")
            return {"status": "success", "period": {"start": from_date.isoformat(), "end": to_date.isoformat(), "day_count": 0}, "users": []}
        
        # === PASS 1: Calculate 5-Pillar Team Maxima per requested period ===
        maxima = _get_company_maxima(db, from_date, to_date)
        max_raw_sp = maxima["max_raw_sp"]
        max_complexity_sp = maxima["max_complexity_sp"]
        max_issues_cnt = maxima["max_issues_cnt"]
        max_founder_sp = maxima["max_founder_sp"]
        global_max_sp = max_raw_sp
            
        logger.info(f"Calculated 5-pillar maxima: raw_sp={max_raw_sp}, complexity={max_complexity_sp}, issues={max_issues_cnt}, founder={max_founder_sp}")
        
        results = []
        
        for target_user_id in target_user_ids:
            user = db.query(models.User).filter(models.User.id == target_user_id).first()
            if not user:
                continue

            # Dynamic indicator matrix: resolve the benchmark from the user's own
            # group maxima (group-level relative scoring), falling back to company-wide.
            user_maxima = _get_company_maxima(db, from_date, to_date, group_id=user.group_id) if user.group_id else maxima
            umax_raw_sp = user_maxima["max_raw_sp"]
            umax_complexity_sp = user_maxima["max_complexity_sp"]
            umax_issues_cnt = user_maxima["max_issues_cnt"]
            umax_founder_sp = user_maxima["max_founder_sp"]
            
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
            from feature_analyzer import stored_feature_weight, stored_feature_detail

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
                                cw = stored_feature_weight(ji)
                                raw_jira_sp_sum += sp
                                complexity_sp_sum += cw

                                mf_res = stored_feature_detail(ji)
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
                "max_raw_sp": umax_raw_sp,
                "max_complexity_sp": umax_complexity_sp,
                "max_issues_cnt": umax_issues_cnt,
                "max_founder_sp": umax_founder_sp
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
                "division_id": user.division_id,
                "division_name": user.division.name if user.division else None,
                "group_id": user.group_id,
                "group_name": user.group_name,
                "supervisor_id": user.supervisor_id,
                "has_subordinates": user.has_subordinates,
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
                    _company_maxima_cache.clear()
                    logger.info("Cache invalidated after comprehensive sync")
                except Exception as e:
                    logger.warning(f"Failed to invalidate cache: {e}")
                
                logger.info(f"Comprehensive sync completed for {len(results)} users")
                mark_job_completed(_db, j_id, {"users_synced": len(results)})
                
            except Exception as e:
                logger.error(f"Error in comprehensive sync: {str(e)}")
                _safe_mark_job_failed(_db, j_id, str(e))
        finally:
            try:
                _db.rollback()
            except Exception:
                pass
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

@app.post("/api/v1/db/kill-locks")
def kill_locks(db: Session = Depends(get_db)):
    """Kill all other Postgres connections to release locks."""
    try:
        db.execute(text("""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = current_database()
              AND pid <> pg_backend_pid();
        """))
        db.commit()
        return {"status": "locks_killed"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
