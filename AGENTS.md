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
- The backend URL for the frontend is `VITE_API_URL` (set in `frontend/.env`, e.g. `http://localhost:8000`). Any new fetch must use `import.meta.env.VITE_API_URL`.
- Components exist in both `X.jsx` and `X.enhanced.jsx` variants, but `src/App.jsx` imports only the non-enhanced ones. The `.enhanced.jsx` files are dead code — edit the plain ones unless you deliberately wire the enhanced variants in.

**Backend (FastAPI):**
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```
- Run from the `backend/` directory. `database.py` resolves the default SQLite path relative to `backend/`, so `sqlite:///./database.db` lands in `backend/database.db`.
- `DATABASE_URL` may point at Postgres — `database.py` rewrites `postgres://` to `postgresql+pg8000://`, so pg8000 is the production driver even though SQLite is used locally.

**DB setup / migration:** Not a manual step. `main.py` `lifespan()` creates tables, auto-migrates columns/indexes via SQLAlchemy Inspector, and seeds default data on startup. `setup_database.py` exists but is an alternative init path.

**Testing:**
- No test runner/pytest — every `test_*.py`, `check_*.py`, `debug_*.py`, `inspect_*.py` script is standalone: `cd backend; python <file>.py`. Many hit the live HRIS/Jira/GitLab APIs or the real DB.
- Most scripts hardcode absolute paths (e.g. `test_all_local.py` has `sys.path.insert(0, 'c:/Users/...')`). Don't treat them as portable fixtures.
- `test_ai_backend.py` / LLM features skip gracefully when `ZAI_API_KEY` is unset (which is the normal local state).

## Key Files & Entry Points

**Backend:**
- `main.py` - FastAPI app: startup migration/seeding in `lifespan()`, all `/api/v1/*` endpoints
- `database.py` - engine + DATABASE_URL handling (SQLite default, pg8000 for Postgres)
- `models.py` - SQLAlchemy ORM models (User, Sprint, KPIRule, KPIEmployeeDaily, etc.)
- `engine.py` - Dynamic KPI calculation engine (safe AST evaluator)
- `yearly_kpi_engine.py` - Yearly/company-wide scoring paths
- `founder_engine.py` - credits founders for their projects
- `feature_analyzer.py` / `ai_formula_generator.py` - feature complexity / AI formula scoring (optional, needs `ZAI_API_KEY`; falls back to deterministic rules)
- `sync_service.py` - Jira/GitLab/attendance sync with retry logic
- `comprehensive_sync.py` - full user sync and daily KPI aggregation
- `multi_board_sync.py` - multi-board Jira support
- `scheduler.py` - in-process BackgroundScheduler + `KPI_CALC_LOCK` that serializes all writes to `kpi_employee_daily`
- `worker.py` - standalone worker; note the sprint/KPI jobs are COMMENTED OUT, only the nightly attendance cron runs
- `webhooks.py` - imported by `main.py` for webhook routes
- `fix_production_db.py` - runs on every deploy (see Deployment) to repair the prod DB

**Frontend (all in `src/`):**
- `App.jsx` - auth + routing + role-gated menus (Configurator = ROLE_ADMIN/MANAGER)
- `components/Dashboard.jsx`, `Subordinates.jsx`, `Configurator.jsx`, `AIIndicatorCreator.jsx` - the active components

## Important Configuration

**Environment (`.env.example`):**
```bash
DATABASE_URL=sqlite:///./database.db
SYNC_SPRINTS_INTERVAL_MINUTES=60
SYNC_KPI_CALCULATION_INTERVAL_MINUTES=60
# OPENROUTER_API_KEY / ZAI_API_KEY / ZAI_MODEL - optional LLM feature scoring (Z.AI GLM Coding Plan)
```
- `VITE_API_URL` lives in `frontend/.env` (not `.env.example`).

**Deployment (nixpacks.toml):**
- Python 3.11 venv in `/opt/venv`
- Build AND start both run `python fix_production_db.py` before launching `uvicorn main:app` on `$PORT`
- Postgres + libpq installed but SQLite is used
- To enable LLM feature scoring in prod, set `ZAI_API_KEY`/`ZAI_MODEL` (and optionally `ZAI_BASE_URL`) as Railway env vars — `.env` is not deployed

## Architecture Gotchas

**DB auto-migration:** `main.py` `lifespan()` (no separate migration files): `create_all()` then Inspector-based `ALTER TABLE` for new columns (e.g. `raw_jira_issues.complexity_score/complexity_detail`, `company_maxima.group_id/division_id`) and index creation. Add new columns here, not in a migration tool. Safe idempotent to re-run on every startup.

**Long-running work = job model:** Heavy operations (KPI calculation, sync, attendance) return a `job_id`; the frontend polls `/api/v1/jobs/{job_id}`. Jobs run in background tasks and need heartbeat/staleness handling — see the git history around "zombie jobs" for the failure modes (Railway redeploys kill background workers). All `kpi_employee_daily` writes must go through `KPI_CALC_LOCK` in `scheduler.py` to avoid deadlocks.

**Authentication:**
- Login (`/api/v1/auth/login`) calls the external HRIS API and returns its token (may take 10-20s; frontend uses 30s abort)
- User profiles synced from HRIS on first login; supervisor subordinates synced in background after login
- Local session verification at `/api/v1/auth/verify` (no HRIS call)

**KPI Calculation:**
- Safe formula evaluation via Python AST (no `eval()`)
- Company-wide relative scoring (5-pillar maxima per period)
- Daily aggregated KPI stored in `KPIEmployeeDaily` table
- AI/LLM feature scoring via Z.AI GLM Coding Plan (`https://api.z.ai/api/coding/paas/v4`, model `glm-5.3`) is optional — off unless `ZAI_API_KEY` is set. Set `ZAI_API_KEY`/`ZAI_MODEL`/`ZAI_BASE_URL` in Railway env (or `backend/.env` locally); never commit the real key.

**Multi-Board Support:** Users can be assigned to multiple Jira boards via `jira_board_ids` JSON field; `current_active_board` tracks the active one; endpoints at `/api/v1/boards` and `/api/v1/users/{user_id}/boards`.

## Security & Token Management

- HRIS tokens stored in-memory only (`_supervisor_token_store` dict)
- Integration tokens (Jira/GitLab) encrypted in DB via `encrypt.py`, decrypted on use
- Tokens masked in GET responses (`••••••••••••••••`)
- No local password storage - auth delegated to HRIS

## Production Debugging

**Database Health Check:**
```bash
curl https://services-kpi-production.up.railway.app/api/v1/db/diagnostics
curl -X POST https://services-kpi-production.up.railway.app/api/v1/db/initialize
```
- 500 errors usually mean missing tables/initial data; check diagnostics first
- Admin repair endpoints: `/api/v1/db/cleanup`, `/api/v1/db/kill-locks`, `/api/v1/db/truncate-raw-data`, `/api/v1/sync/force-prod-fix` (GET)
- Check Railway logs for the actual error (lifespan prints verbose init/migration logs)

## Cache Strategy

- FastAPI in-memory cache (FastAPICache) + `_company_maxima_cache` (30-min TTL, invalidated after sync)
- 60-second expiration on performance endpoints
- Automatic cache invalidation after sync operations

## Documentation Discrepancies

`kpi_dashboard_documentation.md`, `IMPLEMENTATION_SUMMARY.md`, `PREMIUM_UI_IMPLEMENTATION_GUIDE.md` describe a Next.js + PostgreSQL + Redis/Celery architecture, but the actual implementation uses React 19 + Vite, SQLite, and APScheduler in-process. There are also many stale `test_*.py`/`check_*.py` scripts and JSON dumps in `backend/` — treat them as scratch artifacts, not fixtures.

Trust the actual code and `package.json`/`requirements.txt`/`nixpacks.toml` over the documentation.