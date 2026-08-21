import requests
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import SessionLocal, engine
import models
from engine import DynamicKPIEngine
from sync_service import sync_attendance_for_sprint, get_system_token
from multi_board_sync import sync_all_boards_sprints, get_user_active_sprint
from locks import AppLock
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Scheduler")

# Serialises KPI writes. All paths that store rows into kpi_employee_daily
# (manual "Hitung KPI" job, background scheduler job) must go through this lock
# so two workers never deadlock each other with overlapping row locks.
KPI_CALC_LOCK = threading.Lock()

# Configurable scheduler intervals (can be overridden via environment variables)
SYNC_SPRINTS_INTERVAL_MINUTES = int(os.getenv("SYNC_SPRINTS_INTERVAL_MINUTES", "60"))
SYNC_KPI_CALCULATION_INTERVAL_MINUTES = int(os.getenv("SYNC_KPI_CALCULATION_INTERVAL_MINUTES", "60"))

# Concurrency budget for the in-process worker pools.
KPI_CALC_WORKERS = int(os.getenv("KPI_CALC_WORKERS", "5"))
SYNC_USER_WORKERS = int(os.getenv("SYNC_USER_WORKERS", "3"))

scheduler = BackgroundScheduler()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def fetch_sprints_from_jira(db: Session, settings: models.IntegrationSetting, max_retries=2):
    if not (settings and settings.jira_url and settings.jira_token and settings.jira_board_id):
        logger.warning("Jira settings incomplete. Cannot sync sprints.")
        return

    logger.info("Syncing sprints from Jira...")
    
    for attempt in range(max_retries):
        try:
            from encrypt import decrypt_val
            
            # Determine actual token
            actual_token = settings.jira_token
            if settings.jira_token_encrypted:
                actual_token = decrypt_val(settings.jira_token_encrypted)

            if not actual_token:
                return

            jira_auth = (settings.jira_email, actual_token)
            board_url = f"{settings.jira_url}/rest/agile/1.0/board/{settings.jira_board_id}/sprint"
            
            # Fetch active sprints (closed sprints will be synced separately)
            params = {"state": "active"}
            
            resp = requests.get(board_url, auth=jira_auth, params=params, timeout=10)
            if resp.status_code == 200:
                jira_sprints = resp.json().get("values", [])
                
                if not jira_sprints:
                    logger.info("No active sprints found in Jira")
                    return
                
                logger.info(f"Found {len(jira_sprints)} active sprint(s) in Jira")
                
                for js in jira_sprints:
                    sprint_id_str = str(js.get("id"))
                    existing = db.query(models.Sprint).filter(
                        models.Sprint.jira_sprint_id == sprint_id_str
                    ).first()
                    
                    # Use Jira's dates with better fallback
                    s_date = datetime.now()
                    e_date = datetime.now()
                    if js.get("startDate"):
                        s_date = datetime.strptime(js.get("startDate").split("T")[0], "%Y-%m-%d")
                    if js.get("endDate"):
                        e_date = datetime.strptime(js.get("endDate").split("T")[0], "%Y-%m-%d")
                        
                    # For active sprints, always update status to ACTIVE
                    status_val = "ACTIVE"

                    if not existing:
                        # Import active sprints regardless of year (they're still ongoing)
                        logger.info(f"Creating new active sprint: {js.get('name', 'Unknown')} (ID: {sprint_id_str})")
                        new_sprint = models.Sprint(
                            jira_sprint_id=sprint_id_str,
                            sprint_name=js.get("name", "Unknown"),
                            start_date=s_date,
                            end_date=e_date,
                            status=status_val
                        )
                        db.add(new_sprint)
                    else:
                        # Update existing active sprint with latest data
                        existing.sprint_name = js.get("name", "Unknown")
                        existing.start_date = s_date
                        existing.end_date = e_date
                        existing.status = status_val
                        logger.info(f"Updated active sprint: {js.get('name', 'Unknown')} (ID: {sprint_id_str})")
                
                db.commit()
                logger.info(f"Active sprint sync completed. Total: {len(jira_sprints)} sprint(s)")
                return  # Success - exit retry loop
            else:
                logger.warning(f"Failed to fetch Jira sprints: {resp.status_code} (attempt {attempt + 1}/{max_retries})")
                
        except Exception as e:
            logger.error(f"Exception during sprint sync (attempt {attempt + 1}/{max_retries}): {e}")
            import time
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))  # Exponential backoff
    
    logger.warning("Sprint sync failed after all retries")

def fetch_closed_sprints_from_jira(db: Session, settings: models.IntegrationSetting, max_retries=2):
    """Fetch closed sprints from current year for historical data"""
    if not (settings and settings.jira_url and settings.jira_token and settings.jira_board_id):
        logger.warning("Jira settings incomplete. Cannot sync closed sprints.")
        return

    logger.info("Syncing closed sprints from Jira...")
    
    for attempt in range(max_retries):
        try:
            from encrypt import decrypt_val
            
            # Determine actual token
            actual_token = settings.jira_token
            if settings.jira_token_encrypted:
                actual_token = decrypt_val(settings.jira_token_encrypted)

            if not actual_token:
                return

            jira_auth = (settings.jira_email, actual_token)
            board_url = f"{settings.jira_url}/rest/agile/1.0/board/{settings.jira_board_id}/sprint"
            
            # Fetch closed sprints from current year
            params = {"state": "closed"}
            
            resp = requests.get(board_url, auth=jira_auth, params=params, timeout=10)
            if resp.status_code == 200:
                jira_sprints = resp.json().get("values", [])
                
                current_year = datetime.now().year
                closed_sprints_count = 0
                
                for js in jira_sprints:
                    # Get start date for year filtering
                    s_date = datetime.now()
                    if js.get("startDate"):
                        s_date = datetime.strptime(js.get("startDate").split("T")[0], "%Y-%m-%d")
                    
                    # Only import closed sprints from current year
                    if s_date.year != current_year:
                        continue
                    
                    sprint_id_str = str(js.get("id"))
                    existing = db.query(models.Sprint).filter(
                        models.Sprint.jira_sprint_id == sprint_id_str
                    ).first()
                    
                    # Get end date
                    e_date = datetime.now()
                    if js.get("endDate"):
                        e_date = datetime.strptime(js.get("endDate").split("T")[0], "%Y-%m-%d")
                    
                    status_val = "CLOSED"

                    if not existing:
                        logger.info(f"Creating closed sprint: {js.get('name', 'Unknown')} (ID: {sprint_id_str})")
                        new_sprint = models.Sprint(
                            jira_sprint_id=sprint_id_str,
                            sprint_name=js.get("name", "Unknown"),
                            start_date=s_date,
                            end_date=e_date,
                            status=status_val
                        )
                        db.add(new_sprint)
                        closed_sprints_count += 1
                    else:
                        # Update existing closed sprint with latest data
                        existing.sprint_name = js.get("name", "Unknown")
                        existing.start_date = s_date
                        existing.end_date = e_date
                        existing.status = status_val
                
                if closed_sprints_count > 0:
                    db.commit()
                    logger.info(f"Closed sprint sync completed. Added: {closed_sprints_count} sprint(s)")
                else:
                    logger.info("No new closed sprints from current year to sync")
                
                return  # Success - exit retry loop
            else:
                logger.warning(f"Failed to fetch closed Jira sprints: {resp.status_code} (attempt {attempt + 1}/{max_retries})")
                
        except Exception as e:
            logger.error(f"Exception during closed sprint sync (attempt {attempt + 1}/{max_retries}): {e}")
            import time
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))  # Exponential backoff
    
    logger.warning("Closed sprint sync failed after all retries")

def sync_sprints_job():
    db = SessionLocal()
    try:
        settings = db.query(models.IntegrationSetting).first()
        if settings:
            logger.info("Starting multi-board sprints sync from Jira...")
            results = sync_all_boards_sprints(db, settings)
            
            # Log summary
            total_active = sum(r.get("active", 0) for r in results.values())
            total_closed = sum(r.get("closed", 0) for r in results.values())
            total_errors = sum(len(r.get("errors", [])) for r in results.values())
            
            logger.info(f"Multi-board sprint sync completed:")
            logger.info(f"  - Boards synced: {len(results)}")
            logger.info(f"  - Active sprints: {total_active}")
            logger.info(f"  - Closed sprints: {total_closed}")
            if total_errors > 0:
                logger.warning(f"  - Errors: {total_errors}")
            
        # Invalidate cache after sync
        try:
            from fastapi_cache import FastAPICache
            backend = FastAPICache.get_backend()
            if backend:
                FastAPICache.clear()
                logger.info("Cache invalidated after sprint sync")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {e}")
            
    except Exception as e:
        logger.error(f"Error in sync_sprints_job: {e}")
        db.rollback()
    finally:
        db.close()


def sync_data_only_job(supervisor_id=None):
    """
    Sync only data from Jira/GitLab into the local DB without calculating KPI.
    Used by the 'Sync Data' button in the Configurator.
    """
    # Cross-instance guard so two workers never run a full data sync at once.
    _sync_lock = AppLock(engine, "DATA_SYNC")
    if not _sync_lock.try_acquire():
        logger.warning("sync_data_only_job skipped: another instance holds the DATA_SYNC DB lock")
        return {"status": "error", "message": "Sinkronisasi data sedang berjalan oleh instance lain. Tunggu selesai, lalu coba lagi."}

    db = SessionLocal()
    try:
        settings = db.query(models.IntegrationSetting).first()
        if not settings:
            logger.warning("No integration settings found. Cannot sync data.")
            return {"status": "error", "message": "Integration settings not found"}

        # 1. Sync sprints from Jira
        try:
            logger.info("Sync Data: syncing Jira sprints...")
            sync_all_boards_sprints(db, settings)
        except Exception as e:
            logger.error(f"Sync Data: sprint sync failed: {e}")

        # 1b. Discover GitLab projects ONCE per job (the per-user commit sync
        # only re-crawls when the shared 30-min discovery cache is stale).
        try:
            from comprehensive_sync import discover_all_gitlab_projects
            discover_all_gitlab_projects(db, settings)
        except Exception as e:
            logger.error(f"Sync Data: GitLab project discovery failed: {e}")

        # 2. Sync comprehensive data (GitLab commits/MRs + Jira issues/worklogs) for all active users
        from comprehensive_sync import sync_user_comprehensive
        from datetime import datetime as dt

        from sqlalchemy import or_
        query = db.query(models.User).filter(models.User.is_active == True)
        if supervisor_id:
            query = query.filter(or_(models.User.id == supervisor_id, models.User.supervisor_id == supervisor_id))
        users = query.all()
        from datetime import timedelta
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()

        # Parallel per-user sync. Each worker uses its OWN session because
        # SQLAlchemy Session is not thread-safe and a shared session would
        # poison every thread on the first rollback.
        def _sync_one(user):
            from database import SessionLocal as _SL
            s = _SL()
            try:
                result = sync_user_comprehensive(s, user, settings, start_date, end_date)
                return user, result
            except Exception as e:
                logger.error(f"Sync Data: failed for user {user.full_name}: {e}")
                try:
                    s.rollback()
                except Exception:
                    pass
                return user, None
            finally:
                s.close()

        synced_users = 0
        total_records = 0
        with ThreadPoolExecutor(max_workers=SYNC_USER_WORKERS) as pool:
            futures = [pool.submit(_sync_one, u) for u in users]
            for fut in futures:
                user, result = fut.result()
                if result and result.get("status") == "success":
                    synced_users += 1
                    total_records += result.get("total_records", 0)
                logger.info(
                    f"Sync Data: user {user.full_name} -> "
                    f"{result.get('status') if result else 'error'} "
                    f"({result.get('total_records', 0) if result else 0} records)"
                )

        # Invalidate cache after sync
        try:
            from fastapi_cache import FastAPICache
            backend = FastAPICache.get_backend()
            if backend:
                FastAPICache.clear()
                logger.info("Cache invalidated after data sync")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {e}")

        import time
        with open("last_sync.txt", "w") as f:
            f.write(str(int(time.time())))

        logger.info(f"Sync Data completed. Synced {synced_users} users, {total_records} records.")
        return {"status": "success", "users_synced": synced_users, "records": total_records}

    except Exception as e:
        logger.error(f"Error in sync_data_only_job: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
        try:
            _sync_lock.release()
        except Exception:
            pass


def _job_was_cancelled(db: Session, job_id: str) -> bool:
    """True when this job's row was already failed/closed by a newer trigger.

    The old worker thread keeps running even after cancel_running_jobs marks its
    row FAILED. It must notice and stop itself, otherwise it still writes rows
    and run_calc would resurrect it as COMPLETED.
    """
    if not job_id:
        return False
    job = db.query(models.SyncJob).filter(models.SyncJob.id == job_id).first()
    return job is not None and job.status == "FAILED"


def calculate_kpi_only_job(year: int = None, job_id: str = None, progress_cb=None, force: bool = False, supervisor_id: str = None):
    """
    Calculate KPI using data already present in the local DB.
    Does NOT call any external Jira/GitLab sync.
    Used by the 'Hitung KPI' button in the Configurator.

    By default only dates that do not yet have a KPIEmployeeDaily row are
    computed (incremental). Pass force=True to recalculate the whole year.
    """
    if not year:
        year = datetime.now().year

    # Only one KPI calc may write kpi_employee_daily at a time. Multiple parallel
    # runs (repeated user clicks while poll shows a spinner) deadlock on
    # overlapping row locks and every job freezes at the same user.
    if not KPI_CALC_LOCK.acquire(blocking=False):
        logger.warning("calculate_kpi_only_job skipped: another KPI calc is already running")
        return {"status": "error", "message": "Kalkulasi KPI sedang berjalan. Tunggu kalkulasi yang sedang berjalan selesai, lalu coba lagi."}

    # Cross-instance guard: with more than one uvicorn worker/instance the
    # threading lock above is invisible to the other process, so we also take a
    # DB-backed lock. Two Railway workers can never run the calc at the same time.
    _app_lock = AppLock(engine, "KPI_CALC")
    if not _app_lock.try_acquire():
        logger.warning("calculate_kpi_only_job skipped: another instance holds the KPI_CALC DB lock")
        try:
            KPI_CALC_LOCK.release()
        except RuntimeError:
            pass
        return {"status": "error", "message": "Kalkulasi KPI sedang berjalan oleh instance lain. Tunggu selesai, lalu coba lagi."}

    logger.info(f"Starting KPI calculation-only job for year {year} (local DB only)...")
    db = SessionLocal()
    try:
        settings = db.query(models.IntegrationSetting).first()
        if not settings:
            return {"status": "error", "message": "Integration settings not found"}

        from comprehensive_sync import calculate_daily_aggregated_kpi
        from precompute_metrics import compute_all_year_metrics
        from feature_analyzer import calculate_feature_weight
        from sqlalchemy import and_
        from datetime import datetime as dt
        from concurrent.futures import ThreadPoolExecutor

        # Get all active users
        from sqlalchemy import or_
        query = db.query(models.User).filter(models.User.is_active == True)
        if supervisor_id:
            query = query.filter(or_(models.User.id == supervisor_id, models.User.supervisor_id == supervisor_id))
        users = query.all()

        start_date = datetime(year, 1, 1, 0, 0, 0)
        end_date = datetime(year, 12, 31, 23, 59, 59)
        total_users = len(users)

        # Thread-safe progress reporting (main.py's progress_cb shares one bg_db
        # session, so concurrent calls must be serialised).
        _progress_lock = threading.Lock()
        _computed = {"users": 0, "dates": 0}
        _cancelled = {"flag": False}

        def _process_user(user, u_index):
            """Bulk-load + calculate all dates for ONE user in its own session."""
            if _cancelled["flag"]:
                return None
            sdb = SessionLocal()
            try:
                # 1. Activities for the whole year (single query)
                act_q = sdb.query(models.Activity).filter(
                    and_(
                        models.Activity.user_id == user.id,
                        models.Activity.activity_date >= start_date,
                        models.Activity.activity_date <= end_date
                    )
                ).all()
                activities_by_date = {}
                for a in act_q:
                    d = a.activity_date.date() if hasattr(a.activity_date, 'date') else a.activity_date.date()
                    activities_by_date.setdefault(d, []).append(a)

                # 2. Attendance for the whole year (single query)
                att_q = sdb.query(models.AttendanceRecord).filter(
                    and_(
                        models.AttendanceRecord.user_id == user.id,
                        models.AttendanceRecord.date >= start_date.date().isoformat(),
                        models.AttendanceRecord.date <= end_date.date().isoformat()
                    )
                ).all()
                attendance_by_date = {a.date: a for a in att_q}

                # 3. Jira identity (single query)
                ji_ident = sdb.query(models.EmployeeIdentity).filter(
                    and_(
                        models.EmployeeIdentity.user_id == user.id,
                        models.EmployeeIdentity.source == 'jira'
                    )
                ).first()

                # 4. All resolved RawJiraIssue for the year, pre-aggregated into a
                #    per-date complexity sum ONCE (not per date, not per issue).
                #    Fetch only the two needed columns so the huge raw_data JSON
                #    payload is never deserialised for thousands of issues.
                complexity_by_date = {}
                if ji_ident and ji_ident.external_user_id:
                    issues_q = sdb.query(
                        models.RawJiraIssue.resolved_date,
                        models.RawJiraIssue.complexity_score
                    ).filter(
                        models.RawJiraIssue.assignee_account_id == ji_ident.external_user_id,
                        models.RawJiraIssue.resolved_date >= start_date,
                        models.RawJiraIssue.resolved_date <= end_date
                    ).all()
                    for rdate, cscore in issues_q:
                        if not rdate:
                            continue
                        rdate = rdate.date() if hasattr(rdate, 'date') else rdate
                        w = cscore if cscore is not None else 0.0
                        complexity_by_date[rdate] = complexity_by_date.get(rdate, 0.0) + float(w)

                    # 4b. Skip inline backfill to avoid blocking workers on large NULL sets.
                    #     Complexity scores should be populated by sync; for NULL issues,
                    #     we treat as 0 for now. Run /api/v1/kpi/rescore later to backfill.
                    null_count = sdb.query(models.RawJiraIssue).filter(
                        models.RawJiraIssue.assignee_account_id == ji_ident.external_user_id,
                        models.RawJiraIssue.resolved_date >= start_date,
                        models.RawJiraIssue.resolved_date <= end_date,
                        models.RawJiraIssue.complexity_score.is_(None)
                    ).count()
                    if null_count > 0:
                        logger.warning(
                            f"Calculate KPI: user {user.id} has {null_count} NULL complexity issues "
                            f"(treated as 0). Run /api/v1/kpi/rescore to backfill."
                        )

                # 5. Rule + metrics resolved ONCE (not per date!)
                from yearly_kpi_engine import get_rule_and_metrics_for_user, YearlyKPIEngine
                rule, metrics_defs = get_rule_and_metrics_for_user(sdb, user)
                working_days = YearlyKPIEngine.calculate_working_days(
                    datetime(year, 1, 1), datetime(year, 12, 31))

                # 6. Existing daily KPI rows (single query)
                existing_rows = sdb.query(models.KPIEmployeeDaily).filter(
                    and_(
                        models.KPIEmployeeDaily.user_id == user.id,
                        models.KPIEmployeeDaily.date >= start_date,
                        models.KPIEmployeeDaily.date <= end_date
                    )
                ).all()
                daily_by_date = {}
                for r in existing_rows:
                    k = r.date.date() if hasattr(r.date, 'date') else r.date
                    daily_by_date[k] = r

                # Combine unique dates from activities + attendance
                all_dates = set(activities_by_date.keys())
                for date_str in attendance_by_date.keys():
                    try:
                        all_dates.add(dt.strptime(date_str[:10], "%Y-%m-%d").date())
                    except Exception:
                        pass

                # Incremental: only calculate dates with no KPIEmployeeDaily row
                # yet. force=True recalculates the whole year (dates overlap, so
                # rows are updated in place).
                if force:
                    dates_to_calc = sorted(all_dates)
                else:
                    dates_to_calc = sorted(d for d in all_dates if d not in daily_by_date)

                preloaded = {
                    "activities_by_date": activities_by_date,
                    "attendance_by_date": attendance_by_date,
                    "complexity_by_date": complexity_by_date,
                    "jira_ident": ji_ident,
                    "rule_metrics": (rule, metrics_defs),
                    "working_days": working_days,
                    "daily_by_date": daily_by_date,
                    "no_commit": True,
                }

                num_dates = max(len(dates_to_calc), 1)
                for d_idx, d in enumerate(dates_to_calc):
                    if _cancelled["flag"]:
                        break
                    calculate_daily_aggregated_kpi(sdb, user, dt.combine(d, dt.min.time()), preloaded=preloaded)
                    # Progress inside the date loop keeps updated_at fresh even when
                    # a single user takes many minutes.
                    if progress_cb and total_users > 0:
                        with _progress_lock:
                            done_users = _computed["users"]
                        fraction = (done_users + (d_idx + 1) / num_dates) / total_users
                        progress_cb(int(10 + fraction * 80))

                # One commit per user instead of one per date
                sdb.commit()
                return (user.full_name, len(dates_to_calc))
            except Exception as e:
                logger.error(f"Calculate KPI: failed for user {user.id}: {e}")
                sdb.rollback()
                return None
            finally:
                sdb.close()

        calc_count = 0
        total_dates = 0
        with ThreadPoolExecutor(max_workers=KPI_CALC_WORKERS) as pool:
            futures = []
            for idx, u in enumerate(users):
                if _job_was_cancelled(db, job_id):
                    _cancelled["flag"] = True
                    logger.info(f"KPI calc job {job_id} was cancelled; stopping early")
                    break
                futures.append(pool.submit(_process_user, u, idx))
            for fut in futures:
                res = fut.result()
                with _progress_lock:
                    _computed["users"] += 1
                if res:
                    calc_count += 1
                    total_dates += res[1]
                    logger.info(f"Calculate KPI: processed {res[0]} for {res[1]} dates")
                if progress_cb and total_users > 0:
                    with _progress_lock:
                        done_users = _computed["users"]
                    progress_cb(int(10 + done_users / max(total_users, 1) * 80))
                if _cancelled["flag"]:
                    break

        if calc_count is None or _cancelled["flag"]:
            return {"status": "cancelled", "message": "Kalkulasi dibatalkan karena job baru dimulai"}

        # Precompute per-user yearly aggregates + company maxima
        from precompute_metrics import PrecomputeCancelled
        try:
            compute_all_year_metrics(
                db, year,
                is_cancelled=(lambda: _job_was_cancelled(db, job_id)) if job_id else None,
            )
        except PrecomputeCancelled:
            return {"status": "cancelled", "message": "Kalkulasi dibatalkan karena job baru dimulai"}
        except Exception as e:
            logger.error(f"Precompute metrics failed for year {year}: {e}")
            db.rollback()

        # Invalidate all cache
        try:
            from fastapi_cache import FastAPICache
            backend = FastAPICache.get_backend()
            if backend:
                FastAPICache.clear()
                logger.info("Cache invalidated after KPI calculation")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {e}")

        return {"status": "success", "users_processed": calc_count, "dates_processed": total_dates}

    except Exception as e:
        logger.error(f"Error in calculate_kpi_only_job: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
        try:
            _app_lock.release()
        except Exception:
            pass
        try:
            KPI_CALC_LOCK.release()
        except RuntimeError:
            pass


def sync_and_calculate_all_users_job(year: int = None):
    if not year:
        year = datetime.now().year

    if not KPI_CALC_LOCK.acquire(blocking=False):
        logger.info("sync_and_calculate_all_users_job skipped: another KPI calc is already running")
        return

    # Cross-instance guard (see calculate_kpi_only_job).
    _app_lock = AppLock(engine, "KPI_CALC")
    if not _app_lock.try_acquire():
        logger.info("sync_and_calculate_all_users_job skipped: another instance holds the KPI_CALC DB lock")
        try:
            KPI_CALC_LOCK.release()
        except RuntimeError:
            pass
        return

    logger.info(f"Starting background KPI calculation for year {year}...")
    db = SessionLocal()
    try:
        settings = db.query(models.IntegrationSetting).first()
        if not settings:
            return

        # Auto-discover all GitLab projects across all groups
        try:
            from comprehensive_sync import discover_all_gitlab_projects
            discover_all_gitlab_projects(db, settings)
        except Exception as e:
            logger.error(f"Error in automatic GitLab project discovery job: {e}")

        # Ambil IT Division
        default_div = db.query(models.Division).filter(models.Division.code == "IT").first()
        if not default_div:
            return

        # Ambil Rule aktif
        rule = db.query(models.KPIRule).filter(
            models.KPIRule.division_id == default_div.id,
            models.KPIRule.is_active == True
        ).first()
        if not rule:
            return

        metrics_defs = db.query(models.KPIRuleMetric).filter(models.KPIRuleMetric.kpi_rule_id == rule.id).all()
        rule_metrics_list = [
            {
                "metric_key": m.metric_key,
                "weight": float(m.weight),
                "formula_expression": m.formula_expression,
                "variables": m.variables,
                "cap_score": float(m.cap_score)
            } for m in metrics_defs
        ]

        # Get all active users regardless of division
        users = db.query(models.User).filter(
            models.User.is_active == True
        ).all()

        calc_count = 0

        # Process each user individually for the whole year
        for u in users:
            try:
                logger.info(f"Processing KPI for {u.full_name} for year {year}")

                from sync_service import sync_yearly_user_metrics
                # Sync live metrics from Jira / GitLab for the whole year
                synced_metrics = sync_yearly_user_metrics(db, u, year, settings)
                
                # Note: We skip RawMetricsData and SprintKPIScore since they are sprint-bound.
                # Daily KPIs are already inserted during sync_yearly_user_metrics via comprehensive_sync.py
                
                calc_count += 1

            except Exception as e:
                logger.error(f"Error calculating for user {u.id}: {str(e)}")
                db.rollback()

        # Update cache timestamp indicating last sync
        import time
        from fastapi_cache import FastAPICache
        with open("last_sync.txt", "w") as f:
            f.write(str(int(time.time())))

        # Precompute per-user yearly aggregates + company maxima so request
        # paths only read precomputed rows (never rescan raw Jira issues).
        try:
            from precompute_metrics import compute_all_year_metrics
            compute_all_year_metrics(db, year)
        except Exception as e:
            logger.error(f"Precompute metrics failed for year {year}: {e}")
            db.rollback()

        # Invalidate all cache after sync completes
        try:
            backend = FastAPICache.get_backend()
            if backend:
                FastAPICache.clear()
                logger.info("Cache invalidated after KPI calculation sync")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {e}")

        logger.info(f"Completed background KPI calculation. Processed {calc_count} users.")
            
    finally:
        db.close()
        try:
            _app_lock.release()
        except Exception:
            pass
        try:
            KPI_CALC_LOCK.release()
        except RuntimeError:
            pass


def init_scheduler():
    logger.info(f"Initializing scheduler with intervals: Sprint sync every {SYNC_SPRINTS_INTERVAL_MINUTES} min, KPI calculation every {SYNC_KPI_CALCULATION_INTERVAL_MINUTES} min")
    
    # Import CronTrigger for the nightly job
    from apscheduler.triggers.cron import CronTrigger
    
    scheduler.add_job(
        sync_sprints_job, 
        IntervalTrigger(minutes=SYNC_SPRINTS_INTERVAL_MINUTES), 
        id="sync_sprints_job", 
        replace_existing=True,
        max_instances=1,  # Prevent multiple instances running simultaneously
        misfire_grace_time=300  # 5 minutes grace time for missed executions
    )
    
    scheduler.add_job(
        sync_and_calculate_all_users_job, 
        IntervalTrigger(minutes=SYNC_KPI_CALCULATION_INTERVAL_MINUTES), 
        id="sync_calc_job", 
        replace_existing=True,
        max_instances=1,  # Prevent multiple instances running simultaneously
        misfire_grace_time=900  # 15 minutes grace time for missed executions
    )
    
    # Add Nightly Attendance Sync (Runs at 01:00 AM)
    scheduler.add_job(
        sync_attendance_nightly_job,
        CronTrigger(hour=1, minute=0),
        id="sync_attendance_nightly",
        replace_existing=True,
        max_instances=1
    )
    
    scheduler.start()
    logger.info("Scheduler started successfully")

def sync_attendance_nightly_job():
    logger.info("Starting nightly attendance sync job")
    db = SessionLocal()
    try:
        from sync_service import get_system_token, fetch_all_subordinates_attendance
        token = get_system_token()
        if not token:
            logger.error("Failed to get HRIS token for nightly sync")
            return
            
        current_year = datetime.now().year
        records_by_nik = fetch_all_subordinates_attendance(token, current_year)
        
        users = db.query(models.User).filter(models.User.is_active == True).all()
        for user in users:
            records = records_by_nik.get(user.nik, [])
            if not records:
                continue
                
            for rec in records:
                raw_date = rec.get("clockin_time") or rec.get("clockIn") or rec.get("date") or ""
                if not raw_date:
                    continue
                try:
                    d_str = raw_date[:10]
                    d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
                except:
                    continue
                
                # Only sync last 3 days
                if (datetime.now().date() - d_obj).days > 3:
                    continue
                    
                existing = db.query(models.AttendanceRecord).filter(
                    models.AttendanceRecord.user_id == user.id,
                    models.AttendanceRecord.date == d_obj
                ).first()
                
                remark = (rec.get("remarkText") or "").lower()
                is_late = "late" in remark
                
                if existing:
                    existing.status = "PRESENT"
                    existing.is_late = is_late
                else:
                    # Resolve a real sprint at query time (never a hardcoded UUID).
                    default_sprint = (
                        db.query(models.Sprint)
                        .filter(models.Sprint.status == "ACTIVE")
                        .order_by(models.Sprint.start_date.desc())
                        .first()
                    ) or db.query(models.Sprint).order_by(models.Sprint.start_date.desc()).first()
                    sprint_id = default_sprint.id if default_sprint else None
                    att = models.AttendanceRecord(
                        user_id=user.id,
                        date=d_obj,
                        status="PRESENT",
                        is_late=is_late,
                        sprint_id=sprint_id
                    )
                    db.add(att)
                    
        db.commit()
        logger.info("Nightly attendance sync complete")
    except Exception as e:
        logger.error(f"Error in nightly attendance sync: {e}")
        db.rollback()
    finally:
        db.close()
