import requests
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import models
from encrypt import decrypt_val
import time
import logging

logger = logging.getLogger("SyncService")

def parse_iso_datetime(date_str: str) -> datetime:
    # Handle different ISO formats from GitLab
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception:
        # Fallback for simpler format
        return datetime.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S")

def get_system_token(max_retries=3, retry_delay=1) -> str:
    """
    Log in to HRIS backend to retrieve Bearer token for attendance sync with retry logic.
    Credentials come from environment variables (HRIS_SYSTEM_USERNAME / HRIS_SYSTEM_PASSWORD).
    """
    import os
    username = os.getenv("HRIS_SYSTEM_USERNAME", "")
    password = os.getenv("HRIS_SYSTEM_PASSWORD", "")

    if not username or not password:
        logger.warning("No HRIS system credentials configured (HRIS_SYSTEM_USERNAME/PASSWORD). Set them in the environment.")
        return ""

    url = "https://hris-api.atibusinessgroup.com/api/authenticate/mobile"
    for attempt in range(max_retries):
        try:
            res = requests.post(url, json={
                "username": username,
                "password": password
            }, timeout=8)
            if res.status_code == 200:
                token = res.json().get("id_token", "")
                logger.info(f"HRIS system login successful on attempt {attempt + 1}")
                return token
            else:
                logger.warning(f"System login returned status {res.status_code} (attempt {attempt + 1}/{max_retries}): {res.text[:200]}")
        except Exception as e:
            logger.warning(f"Failed to fetch system login token (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
    return ""

# ─────────────────────────────────────────────────────────────
# ATTENDANCE SYNC & LATE CALCULATION
# ─────────────────────────────────────────────────────────────

def get_working_days(start_date: datetime, end_date: datetime) -> list:
    """
    Return list of working day date strings (Mon-Fri) within the sprint range.
    """
    working_days = []
    current = start_date.date() if isinstance(start_date, datetime) else start_date
    end = end_date.date() if isinstance(end_date, datetime) else end_date
    
    while current <= end:
        # 0=Monday, 6=Sunday — include Mon-Fri only
        if current.weekday() < 5:
            working_days.append(current.isoformat())
        current += timedelta(days=1)
    
    return working_days

def fetch_timesheet_schedules(max_retries=3, retry_delay=2) -> dict:
    """
    Fetch shift definitions from talent-backend timesheets API with retry logic.
    Returns dict of {code: clock_in_time}, e.g. {"G1": "09:00:00"}
    """
    token = get_system_token()
    if not token:
        return {"DEFAULT": "09:00:00"}
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    
    for attempt in range(max_retries):
        try:
            res = requests.get(
                "https://hris-api.atibusinessgroup.com/api/app/timesheets?page=0&size=100",
                headers=headers, timeout=8
            )
            if res.status_code == 200:
                data = res.json()
                schedules = {}
                for item in data:
                    code = item.get("code", "")
                    clock_in = item.get("clockIn", "09:00:00")
                    if code:
                        schedules[code] = clock_in
                if schedules:
                    return schedules
            else:
                logger.warning(f"Timesheet API returned status {res.status_code} (attempt {attempt + 1}/{max_retries})")
        except Exception as e:
            logger.warning(f"Failed to fetch timesheet schedules (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
    
    return {"DEFAULT": "09:00:00"}


_attendance_cache = {}

def fetch_all_subordinates_attendance(token: str, year: int) -> dict:
    """
    Fetch attendance for ALL subordinates at once using the manager's token.
    Endpoint: /api/app/users/attendances-new?page=X&size=Y&sort=clockin_timesheet
    Returns dict grouped by NIK: {nik: [records]}
    Filters records to the target year client-side.
    """
    from datetime import datetime, timedelta
    cache_key = f"{token}_{year}"
    if cache_key in _attendance_cache:
        cache_time, data = _attendance_cache[cache_key]
        # Cache for 10 minutes to avoid repeated slow fetches during background job loops
        if datetime.now() - cache_time < timedelta(minutes=10):
            logger.info(f"[Attendance] Using cached data for year {year}")
            return data

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    
    records_by_nik = {}
    page = 0
    page_size = 2000  # Increased to 2000 to fetch all in one go and bypass HRIS API pagination bugs
    total_fetched = 0
    
    start_str = f"{year}-01-01"
    end_str = f"{year}-12-31"
    
    while True:
        url = (
            f"https://hris-api.atibusinessgroup.com/api/app/users/attendances-new"
            f"?page={page}&size={page_size}&sort=clockin_timesheet"
            f"&startDate={start_str}&endDate={end_str}"
        )
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code != 200:
                logger.warning(f"[Attendance] attendances-new page={page} → HTTP {res.status_code}: {res.text[:200]}")
                if res.status_code == 401:
                    logger.error("[Attendance] HRIS token invalid or expired")
                    return {}
                break
            
            data = res.json()
            
            # Handle both list and paginated-dict response shapes
            if isinstance(data, list):
                records = data
                is_last = len(data) < page_size
            elif isinstance(data, dict):
                records = data.get("content", data.get("data", []))
                is_last = data.get("last", len(records) < page_size)
            else:
                break
            
            if not records:
                logger.info(f"[Attendance] No records found on page {page}")
                break
            
            # Group by NIK, filter to target year
            for rec in records:
                # Parse date from clockin_time, clockIn or date field
                raw_date = rec.get("clockin_time") or rec.get("clockIn") or rec.get("date") or ""
                try:
                    rec_year = int(raw_date[:4]) if raw_date else 0
                except Exception:
                    rec_year = 0
                
                if rec_year != year:
                    continue  # Skip records outside target year
                
                memployee = rec.get("memployee") or {}
                nik = memployee.get("nik") or rec.get("nik") or str(rec.get("employee_id", ""))
                if not nik:
                    continue
                
                if nik not in records_by_nik:
                    records_by_nik[nik] = []
                records_by_nik[nik].append(rec)
            
            total_fetched += len(records)
            logger.info(f"[Attendance] Page {page}: fetched {len(records)} records, total={total_fetched}, unique NIKs={len(records_by_nik)}")
            
            if is_last:
                break
            page += 1
            
        except Exception as e:
            logger.error(f"[Attendance] Error fetching attendances-new page={page}: {e}")
            break
    
    logger.info(f"[Attendance] Fetched {total_fetched} total records for year {year}, {len(records_by_nik)} unique NIKs")
    _attendance_cache[cache_key] = (datetime.now(), records_by_nik)
    return records_by_nik


def parse_attendance_summary(records: list, working_days_count: int) -> dict:
    """
    Parse attendance records into attendance summary.
    Uses 'remarkText' field from HRIS: 'Late', 'Normal', 'Early Leave'.
    """
    present_count = 0
    late_count = 0
    
    for rec in records:
        clock_in = rec.get("clockIn") or rec.get("clockin_time")
        if not clock_in:
            continue  # No clock-in = absent
        
        present_count += 1
        remark = (rec.get("remarkText") or "").lower()
        if "late" in remark:
            late_count += 1
    
    absent_count = max(0, working_days_count - present_count)
    late_pct = round((late_count / present_count * 100) if present_count > 0 else 0, 2)
    normal_pct = round(100 - late_pct, 2) if present_count > 0 else 0.0
    
    # Ensure present_count is at least working_days_count to avoid division by zero
    if present_count == 0:
        present_count = 0  # Keep 0 if truly no attendance
        late_pct = 0.0
        normal_pct = 0.0
    
    return {
        "attendance_days": float(present_count),
        "target_days": float(working_days_count),
        "late_count": float(late_count),
        "late_percentage": float(late_pct),
        "normal_percentage": float(normal_pct),
        "absent_count": float(absent_count)
    }


def sync_attendance_for_year(db: Session, users: list, year: int, token_override: str = None) -> dict:
    """
    Sync attendance for all subordinates using /app/users/attendances-new endpoint.
    Uses ONE paginated call to get ALL subordinates' data (manager's token required).
    Groups by NIK and maps to user IDs. Caches to KPIEmployeeDaily in SQLite.
    """
    token = token_override if token_override else get_system_token()
    if not token:
        logger.warning("[Attendance Year Sync] No token available, skipping")
        return {}
    
    working_days = get_working_days(datetime(year, 1, 1), datetime(year, 12, 31))
    target_days = len(working_days)
    
    # Build NIK → user mapping for fast lookup
    nik_to_user = {u.nik: u for u in users if u.nik}
    logger.info(f"[Attendance Year Sync] NIK mapping: {len(nik_to_user)} users with NIK out of {len(users)} total users")
    
    logger.info(f"[Attendance Year Sync] Fetching year={year} for {len(users)} users via attendances-new...")
    records_by_nik = fetch_all_subordinates_attendance(token, year)
    
    if not records_by_nik:
        logger.warning("[Attendance Year Sync] No attendance records fetched from HRIS API")
        return {}
    
    results = {}
    cache_date = datetime(year, 1, 1)
    
    for user in users:
        nik = user.nik
        user_records = records_by_nik.get(nik, [])
        
        if not user_records:
            logger.info(f"[Attendance] {user.full_name} (NIK={nik}): no attendance records found for {year}")
            summary = {
                "attendance_days": 0.0, "target_days": float(target_days),
                "late_count": 0.0, "late_percentage": 0.0,
                "normal_percentage": 100.0, "absent_count": float(target_days)
            }
        else:
            summary = parse_attendance_summary(user_records, target_days)
            logger.info(
                f"[Attendance] {user.full_name}: "
                f"{int(summary['attendance_days'])}/{target_days} hadir, "
                f"{int(summary['late_count'])} terlambat ({summary['late_percentage']}%)"
            )
        
        results[user.id] = summary
        
        # Insert into AttendanceRecord so comprehensive_sync can pick it up properly
        try:
            affected_dates = set()
            for rec in user_records:
                raw_date = rec.get("clockin_time") or rec.get("clockIn") or rec.get("date") or ""
                if not raw_date:
                    continue
                
                try:
                    d_str = raw_date[:10]
                    d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
                except:
                    continue
                
                # Check if already exists
                existing = db.query(models.AttendanceRecord).filter(
                    models.AttendanceRecord.user_id == user.id,
                    models.AttendanceRecord.date == d_str
                ).first()
                
                remark = (rec.get("remarkText") or "").lower()
                is_late = "late" in remark
                
                if existing:
                    existing.status = "PRESENT"
                    existing.is_late = is_late
                else:
                    # Find any default sprint to attach
                    default_sprint = db.query(models.Sprint).first()
                    sprint_id = default_sprint.id if default_sprint else "cd7c558a-dfb9-49b9-8438-5b7f58aae49f"
                    
                    # If the hardcoded sprint doesn't exist, we must create a dummy one to satisfy foreign key constraints
                    if not default_sprint:
                        dummy = db.query(models.Sprint).filter(models.Sprint.id == sprint_id).first()
                        if not dummy:
                            # Create dummy sprint
                            from datetime import date
                            dummy = models.Sprint(
                                id=sprint_id,
                                sprint_name="Default Backlog / Untracked",
                                start_date=date(2020, 1, 1),
                                end_date=date(2030, 12, 31),
                                status="active"
                            )
                            db.add(dummy)
                            db.commit()

                    att = models.AttendanceRecord(
                        user_id=user.id,
                        date=d_str,
                        status="PRESENT",
                        is_late=is_late,
                        sprint_id=sprint_id
                    )
                    db.add(att)
                
                affected_dates.add(d_obj)
            
            db.commit()
            
            # Clean up the old corrupted yearly cache from KPIEmployeeDaily if exists
            bad_cache = db.query(models.KPIEmployeeDaily).filter(
                models.KPIEmployeeDaily.user_id == user.id,
                models.KPIEmployeeDaily.date == cache_date,
                models.KPIEmployeeDaily.attendance_days > 1
            ).first()
            if bad_cache:
                bad_cache.attendance_days = 0
                db.commit()
            
            # Repopulate daily KPI records so the API returns the correct total_attendance_days
            from comprehensive_sync import calculate_daily_aggregated_kpi
            for d_obj in affected_dates:
                dt_midnight = datetime.combine(d_obj, datetime.min.time())
                calculate_daily_aggregated_kpi(db, user, dt_midnight)
                
        except Exception as e:
            logger.error(f"[Attendance] DB save failed for {user.full_name}: {e}")
            db.rollback()
    
    logger.info(f"[Attendance Year Sync] Done: {len(results)} karyawan untuk tahun {year}")
    return results


def sync_attendance_for_sprint(db: Session, sprint: models.Sprint, users: list, token_override: str = None) -> dict:
    """
    Sprint-level attendance sync using /app/users/attendances-new endpoint.
    """
    working_days = get_working_days(sprint.start_date, sprint.end_date)
    target_days = len(working_days) or 10
    year = sprint.start_date.year
    
    token = token_override if token_override else get_system_token()
    if not token:
        logger.warning("[Attendance Sprint Sync] No token available")
        return {u.id: {"attendance_days": float(target_days), "target_days": float(target_days),
                       "late_count": 0.0, "late_percentage": 0.0,
                       "normal_percentage": 100.0, "absent_count": 0.0} for u in users}
    
    # Fetch all and filter to sprint date range
    records_by_nik = fetch_all_subordinates_attendance(token, year)
    sprint_start = sprint.start_date.strftime("%Y-%m-%d")
    sprint_end = sprint.end_date.strftime("%Y-%m-%d")
    
    results = {}
    for user in users:
        nik = user.nik
        all_records = records_by_nik.get(nik, [])
        # Filter to sprint range
        sprint_records = []
        for rec in all_records:
            raw_date = (rec.get("clockIn") or rec.get("date") or "")[:10]
            if sprint_start <= raw_date <= sprint_end:
                sprint_records.append(rec)
        results[user.id] = parse_attendance_summary(sprint_records, target_days)
    
    return results

def calculate_late_status(clock_in_str: str, scheduled_in_str: str = "09:00:00") -> dict:
    """
    Compare actual clock-in time against scheduled time.
    Returns: {"is_late": bool, "late_minutes": int}
    """
    try:
        actual = datetime.strptime(clock_in_str, "%H:%M:%S")
        scheduled = datetime.strptime(scheduled_in_str, "%H:%M:%S")
        
        diff_minutes = int((actual - scheduled).total_seconds() / 60)
        
        if diff_minutes > 0:
            return {"is_late": True, "late_minutes": diff_minutes}
        return {"is_late": False, "late_minutes": 0}
    except Exception:
        return {"is_late": False, "late_minutes": 0}

def sync_jira_by_date_range(db: Session, user: models.User, settings: models.IntegrationSetting, start_date: str, end_date: str) -> dict:
    """
    Ambil SEMUA tiket Jira yang di-assign ke user dalam date range.
    Tidak perlu board ID — langsung JQL.
    """
    metrics = {"jira_sp": 0.0, "jira_issues_completed": 0.0}
    
    if not settings.jira_url or not settings.jira_token_encrypted or not user.jira_account_id:
        return metrics
        
    jira_token = decrypt_val(settings.jira_token_encrypted)
    jira_auth = (settings.jira_email, jira_token)
    jira_url = settings.jira_url.rstrip("/")
    
    jql = f'assignee = "{user.jira_account_id}" AND resolved >= "{start_date}" AND resolved <= "{end_date}"'
    search_url = f"{jira_url}/rest/api/3/search/jql"
    search_payload = {
        "jql": jql,
        "fields": ["summary", "status", "customfield_10016"], # customfield_10016 is usually SP
        "maxResults": 1000
    }
    
    try:
        resp = requests.post(search_url, auth=jira_auth, json=search_payload, timeout=10)
        if resp.status_code == 200:
            issues = resp.json().get("issues", [])
            jira_sp = 0.0
            jira_completed = 0
            sp_field = settings.jira_sp_field or "customfield_10016"
            
            for issue in issues:
                fields = issue.get("fields", {})
                status_name = fields.get("status", {}).get("name", "").lower()
                is_done = status_name in ["done", "closed", "resolved", "complete", "finished", "ready for release"]
                
                if is_done:
                    jira_completed += 1
                    sp_val = fields.get(sp_field)
                    if sp_val:
                        try:
                            jira_sp += float(sp_val)
                        except (ValueError, TypeError):
                            pass
                            
            metrics["jira_sp"] = jira_sp
            metrics["jira_issues_completed"] = float(jira_completed)
            logger.info(f"Jira sync success for {user.full_name}: {jira_completed} issues, {jira_sp} SP")
        else:
            logger.warning(f"Jira sync failed: {resp.status_code} - {resp.text}")
    except Exception as e:
        logger.error(f"Jira sync error: {str(e)}")
        
    return metrics
def sync_yearly_user_metrics(db, user, year, settings, attendance_data=None):
    import logging
    import json
    from comprehensive_sync import sync_user_comprehensive, calculate_daily_aggregated_kpi
    from sqlalchemy import and_
    from datetime import datetime, timedelta
    import models

    logger = logging.getLogger("SyncYearlyUserMetrics")
    
    metrics = {
        "jira_sp": 0.0,
        "gitlab_mr_merged": 0.0,
        "attendance_days": 0.0,
        "target_days": 0.0,
        "late_percentage": 0.0,
        "normal_percentage": 0.0,
        "late_count": 0.0
    }
    
    try:
        start_date = datetime(year, 1, 1, 0, 0, 0)
        end_date = datetime(year, 12, 31, 23, 59, 59)
        
        # 1. Sync comprehensive data
        sync_result = sync_user_comprehensive(db, user, settings, start_date, end_date)
        logger.info(f"Comprehensive sync result for {user.full_name} ({year}): {sync_result}")
        
        # 2. Aggregate data into KPIEmployeeDaily for the whole year
        activity_dates_q = db.query(models.Activity.activity_date).filter(
            and_(
                models.Activity.user_id == user.id,
                models.Activity.activity_date >= start_date.date(),
                models.Activity.activity_date <= end_date.date()
            )
        ).distinct().all()
        
        att_dates_q = db.query(models.AttendanceRecord.date).filter(
            and_(
                models.AttendanceRecord.user_id == user.id,
                models.AttendanceRecord.date >= start_date.date().isoformat(),
                models.AttendanceRecord.date <= end_date.date().isoformat()
            )
        ).distinct().all()
        
        # Combine unique dates
        all_dates = set()
        for r in activity_dates_q:
            if r[0]: 
                if isinstance(r[0], datetime):
                    all_dates.add(r[0].date())
                elif hasattr(r[0], 'year'):  # datetime.date
                    all_dates.add(r[0])
                elif isinstance(r[0], str):
                    try:
                        all_dates.add(datetime.strptime(r[0][:10], "%Y-%m-%d").date())
                    except:
                        pass
        for r in att_dates_q:
            if r[0]:
                if isinstance(r[0], datetime):
                    all_dates.add(r[0].date())
                elif hasattr(r[0], 'year'):
                    all_dates.add(r[0])
                elif isinstance(r[0], str):
                    try:
                        all_dates.add(datetime.strptime(r[0][:10], "%Y-%m-%d").date())
                    except:
                        pass
                    
        # Calculate daily aggregated KPI for each date
        for d in sorted(all_dates):
            dt = datetime.combine(d, datetime.min.time())
            calculate_daily_aggregated_kpi(db, user, dt)
            
    except Exception as e:
        logger.error(f"Error syncing yearly user metrics for {user.full_name}: {e}")
        db.rollback()
        
    return metrics
