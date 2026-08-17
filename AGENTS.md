# KPI Dashboard - Agent Guide

## Architecture

**Frontend:** React 19 + Vite (NOT Next.js as docs suggest)
**Backend:** FastAPI + SQLAlchemy + SQLite (NOT PostgreSQL)
**Database:** SQLite with auto-migration on startup
**Auth:** External HRIS API (`https://hris-api.atibusinessgroup.com`) - no local auth

## Development Commands

**Frontend (React + Vite):**
```bash
cd frontend
npm run dev          # Start dev server (port 5173)
npm run build        # Production build
npm run lint         # Run oxlint
npm run preview      # Preview production build
```

**Backend (FastAPI):**
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Database Setup:**
```bash
cd backend
python setup_database.py    # Initialize production database
```

**Testing:**
- No unified test command - run individual test files: `python test_db.py`, `python test_api.py`, etc.
- Many debugging scripts available: `check_*.py`, `debug_*.py`, `test_*.py`

## Key Files & Entry Points

**Backend:**
- `main.py` - FastAPI app entry point, API endpoints
- `models.py` - SQLAlchemy ORM models (User, Sprint, KPIRule, etc.)
- `engine.py` - Dynamic KPI calculation engine (safe AST evaluator)
- `sync_service.py` - Jira/GitLab sync with retry logic
- `scheduler.py` - Background sync jobs (APScheduler)
- `comprehensive_sync.py` - Full user sync and daily KPI calculation
- `multi_board_sync.py` - Multi-board Jira support

**Frontend:**
- `src/App.jsx` - Main app with auth and routing
- `src/components/Dashboard.jsx` - Individual KPI dashboard
- `src/components/Subordinates.jsx` - Team management view
- `src/components/Configurator.jsx` - KPI rule configuration

## Important Configuration

**Environment (`.env.example`):**
```bash
DATABASE_URL=sqlite:///./database.db
SYNC_SPRINTS_INTERVAL_MINUTES=60
SYNC_KPI_CALCULATION_INTERVAL_MINUTES=60
```

**Deployment (nixpacks.toml):**
- Uses Python 3.11 venv in `/opt/venv`
- Backend runs with uvicorn on `$PORT`
- Postgres and libpq installed but SQLite is used

## Architecture Gotchas

**Database Migrations:**
- Auto-migration runs on app startup via `lifespan()` context manager
- Manual column additions in `main.py` (lines 38-58) for group_id/group_name
- No separate migration files - modify SQL in `lifespan()`

**Authentication:**
- Login endpoint calls external HRIS API and returns its token
- User profiles synced from HRIS on first login
- Supervisor subordinates synced in background after login
- Local session verification at `/api/v1/auth/verify` (no HRIS call)

**CORS Configuration:**
- Multiple origins configured: localhost:5173/5174/3000 and `https://kpi-dashboard-xi-murex.vercel.app`
- All methods/headers allowed
- Used for local dev + Vercel deployment

**Data Sync:**
- Jira sync per-user based on `jira_account_id` mapping
- GitLab sync per-user based on `gitlab_username` mapping
- Attendance sync requires HRIS admin endpoint access
- Background tasks prevent blocking during sync
- Cache invalidation runs after sync completes

**KPI Calculation:**
- Safe formula evaluation using Python AST (no `eval()`)
- Company-wide relative scoring (5-pillar maxima per period)
- Founders get credited for their projects (founder_engine.py)
- Feature complexity weighting (feature_analyzer.py)
- Daily aggregated KPI stored in `KPIEmployeeDaily` table

**Multi-Board Support:**
- Users can be assigned to multiple Jira boards via `jira_board_ids` JSON field
- Current active board tracked in `current_active_board` column
- Sync operations iterate through assigned boards
- Board management endpoints at `/api/v1/boards` and `/api/v1/users/{user_id}/boards`

## Security & Token Management

- HRIS tokens stored in-memory only (`_supervisor_token_store` dict)
- Integration tokens (Jira/GitLab) encrypted in DB via `encrypt.py`
- Tokens masked in GET responses (`••••••••••••••••`)
- No local password storage - auth delegated to HRIS

## Production Debugging

**Database Health Check:**
```bash
# Check database status
curl https://services-kpi-production.up.railway.app/api/v1/db/diagnostics

# Force database initialization
curl -X POST https://services-kpi-production.up.railway.app/api/v1/db/initialize
```

**Common Production Issues:**
- 500 errors usually mean missing database tables or initial data
- Use `/api/v1/db/diagnostics` to check database health
- Run `/api/v1/db/initialize` to set up initial divisions and integration settings
- Check Railway logs for specific error messages

**Database Auto-Migration:**
- Runs on app startup via `lifespan()` context manager
- Creates tables, adds columns, seeds default divisions
- Won't overwrite existing data
- Safe to run multiple times

## Testing & Debugging

- Many test files with different focus areas: `test_api.py`, `test_db.py`, `test_attendance_logic.py`
- Debugging scripts: `check_*.py`, `debug_*.py`, `inspect_*.py`
- Manual sync triggers: `/api/v1/sync/trigger`, `/api/v1/sync/force-prod-fix`
- Job status monitoring: `/api/v1/sync/status`, `/api/v1/jobs/{job_id}`

## Cache Strategy

- FastAPI in-memory cache (FastAPICache)
- 60-second expiration on performance endpoints
- Automatic cache invalidation after sync operations
- Cache cleared on yearly sync endpoint

## Documentation Discrepancies

The `kpi_dashboard_documentation.md` file describes a Next.js + PostgreSQL architecture, but the actual implementation uses:
- React 19 + Vite (NOT Next.js)
- SQLite (NOT PostgreSQL)
- No Redis/Celery (uses APScheduler in-process)
- Docker Compose not actively used (nixpacks.toml for deployment)

Trust the actual code and `package.json`/`requirements.txt` over the documentation.