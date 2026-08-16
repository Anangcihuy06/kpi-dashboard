"""
Comprehensive Activity Sync Service
Implements the full workflow from GitLab/Jira documentation
"""

import requests
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import models
from database import SessionLocal
import logging
from encrypt import decrypt_val
from feature_analyzer import calculate_feature_weight
import concurrent.futures
from typing import List, Dict, Any, Optional

def fetch_project_commits(project_id, author_query, gitlab_url, headers, start_date_str, end_date_str):
    commits_url = f"{gitlab_url}/api/v4/projects/{project_id}/repository/commits"
    commits_params = {
        "author": author_query,
        "since": start_date_str,
        "until": end_date_str,
        "per_page": 100
    }
    try:
        response = requests.get(commits_url, headers=headers, params=commits_params, timeout=10)
        if response.status_code == 200:
            batch = response.json()
            if isinstance(batch, list):
                return batch
    except Exception:
        pass
    return []
logger = logging.getLogger("ComprehensiveSync")

# ─────────────────────────────────────────────────────────────
# IDENTITY MAPPING
# ─────────────────────────────────────────────────────────────

def discover_user_identities(db: Session, user: models.User, settings: models.IntegrationSetting) -> Dict[str, Any]:
    """
    Attempt to discover Jira and GitLab identities for a user based on their email or full_name.
    """
    identities = {"jira": None, "gitlab": None}
    
    # --- HARDCODED PATCH FOR PRODUCTION PROXY USERS ---
    KNOWN_MAPPINGS = {
        "01.04.19.1905": {"jira": "5de71ecb8743750d00b7fbf5", "gitlab": "anang"},
        "18.11.22.3063": {"jira": "63bbbbfa50b9490924dc02d0", "gitlab": "adian.rhamadhan"},
        "13.04.26.4918": {"jira": "5de480fe3384720d1879bce3", "gitlab": "billy93"},
        "31.03.23.3190": {"jira": "5de480fe3384720d1879bce3", "gitlab": "billy93"},  # PROD NIK for Billy
        "06.01.23.3097": {"jira": "63bb8aeb2a526608c54f51a7", "gitlab": "ansha.cerbia"},
        "01.10.19.2239": {"jira": "5de8eafb7eb2280d03ca4f86", "gitlab": "bayu.prasetya"},
        "10.06.19.1979": {"jira": "5de71eba7eb2280d03ca30d6", "gitlab": "imamul.muttaqin"},
        "04.01.21.2435": {"jira": "6001479ad36496013924f9da", "gitlab": "azhari"},
        "05.03.18.1603": {"jira": "5de71ebe4ae7b80d0d1a28c4", "gitlab": "syailendra"},
        "01.05.13.500": {"jira": "5d1f43ace037b10d210cd6f4", "gitlab": "ryan"}
    }
    changed = False
    if user.nik in KNOWN_MAPPINGS:
        patch = KNOWN_MAPPINGS[user.nik]
        if not user.jira_account_id or user.jira_account_id.startswith("jira_user_"):
            user.jira_account_id = patch["jira"]
            changed = True
        if not user.gitlab_username or user.gitlab_username.startswith("gitlab_user_"):
            user.gitlab_username = patch["gitlab"]
            changed = True
            
    if not user.jira_account_id:
        user.jira_account_id = f"jira_user_{user.id}"
        changed = True
    if not user.gitlab_username:
        user.gitlab_username = f"gitlab_user_{user.id}"
        changed = True
        
    if changed:
        db.commit()
        
    # Also ensure EmployeeIdentity records exist for the known mappings
    if user.nik in KNOWN_MAPPINGS:
        patch = KNOWN_MAPPINGS[user.nik]
        # Check and create Jira identity
        existing_jira = db.query(models.EmployeeIdentity).filter(
            and_(models.EmployeeIdentity.user_id == user.id, models.EmployeeIdentity.source == "jira")
        ).first()
        if not existing_jira:
            new_jira = models.EmployeeIdentity(
                user_id=user.id,
                source="jira",
                external_user_id=patch["jira"],
                username=user.email or user.full_name,
                full_name=user.full_name,
                is_verified=True
            )
            db.add(new_jira)
            
        # Check and create GitLab identity
        existing_gitlab = db.query(models.EmployeeIdentity).filter(
            and_(models.EmployeeIdentity.user_id == user.id, models.EmployeeIdentity.source == "gitlab")
        ).first()
        if not existing_gitlab:
            new_gitlab = models.EmployeeIdentity(
                user_id=user.id,
                source="gitlab",
                external_user_id=patch["gitlab"], # GitLab uses external_user_id as user id, but for now we put username
                username=patch["gitlab"],
                full_name=user.full_name,
                is_verified=True
            )
            db.add(new_gitlab)
            
        db.commit()
    # ------------------------------------------------
    
    # Get existing identities
    existing_identities = db.query(models.EmployeeIdentity).filter(
        models.EmployeeIdentity.user_id == user.id
    ).all()
    
    for identity in existing_identities:
        identities[identity.source] = {
            "external_user_id": identity.external_user_id,
            "username": identity.username,
            "email": identity.email,
            "verified": identity.is_verified
        }
    
    # Try to discover GitLab identity
    if settings.gitlab_token_encrypted and user.gitlab_username:
        try:
            gitlab_token = decrypt_val(settings.gitlab_token_encrypted)
            gitlab_url = settings.gitlab_url.rstrip("/")
            
            # Get GitLab user info
            user_url = f"{gitlab_url}/api/v4/users"
            
            # If the username is a placeholder, try searching by email
            if user.gitlab_username.startswith("gitlab_user_"):
                params = {"search": user.email, "per_page": 1} if user.email else {"username": user.gitlab_username, "per_page": 1}
                response = requests.get(user_url, headers={"PRIVATE-TOKEN": gitlab_token}, 
                                    params=params, timeout=10)
                
                # Fallback to full_name if search returned empty
                if response.status_code == 200 and not response.json():
                    logger.info(f"GitLab API returned empty for {user.email or user.gitlab_username}, falling back to full_name {user.full_name}")
                    params = {"search": user.full_name, "per_page": 1}
                    response = requests.get(user_url, headers={"PRIVATE-TOKEN": gitlab_token}, 
                                        params=params, timeout=10)
            else:
                params = {"username": user.gitlab_username, "per_page": 1}
                response = requests.get(user_url, headers={"PRIVATE-TOKEN": gitlab_token}, 
                                    params=params, timeout=10)
            
            if response.status_code == 200:
                gitlab_users = response.json()
                if gitlab_users:
                    gitlab_user = gitlab_users[0]
                    
                    # Store back the real username if it was mocked
                    if user.gitlab_username.startswith("gitlab_user_"):
                        user.gitlab_username = gitlab_user.get("username")
                        db.commit()

                    
                    # Update or create identity
                    gitlab_identity = db.query(models.EmployeeIdentity).filter(
                        and_(
                            models.EmployeeIdentity.user_id == user.id,
                            models.EmployeeIdentity.source == "gitlab",
                            models.EmployeeIdentity.external_user_id == str(gitlab_user.get("id"))
                        )
                    ).first()
                    
                    identity_data = {
                        "user_id": user.id,
                        "source": "gitlab",
                        "external_user_id": str(gitlab_user.get("id")),
                        "username": gitlab_user.get("username"),
                        "email": gitlab_user.get("email"),
                        "full_name": gitlab_user.get("name"),
                        "is_verified": True
                    }
                    
                    if not gitlab_identity:
                        gitlab_identity = models.EmployeeIdentity(**identity_data)
                        db.add(gitlab_identity)
                    else:
                        gitlab_identity.email = gitlab_user.get("email")
                        gitlab_identity.full_name = gitlab_user.get("name")
                        gitlab_identity.is_verified = True
                    
                    db.commit()
                    
                    identities["gitlab"] = {
                        "external_user_id": str(gitlab_user.get("id")),
                        "username": gitlab_user.get("username"),
                        "email": gitlab_user.get("email"),
                        "verified": True
                    }
                    
                    logger.info(f"Discovered GitLab identity for {user.full_name}: {gitlab_user.get('username')}")
                else:
                    logger.warning(f"GitLab API returned empty user list for {user.gitlab_username}")
            else:
                logger.warning(f"GitLab API failed for {user.gitlab_username} with status {response.status_code}: {response.text}")
                    
        except Exception as e:
            logger.error(f"Error discovering GitLab identity for {user.full_name}: {str(e)}")
    
    # Try to discover Jira identity
    if settings.jira_token_encrypted and user.jira_account_id:
        try:
            jira_token = decrypt_val(settings.jira_token_encrypted)
            jira_auth = (settings.jira_email, jira_token)
            jira_url = settings.jira_url.rstrip("/")
            
            # Get Jira user info
            if user.jira_account_id.startswith("jira_user_"):
                user_search_url = f"{jira_url}/rest/api/3/user/search"
                params = {"query": user.email} if user.email else {"query": user.full_name}
                response = requests.get(user_search_url, auth=jira_auth, params=params, timeout=10)
                
                # Fallback to full_name if search returned empty
                if response.status_code == 200 and not response.json():
                    logger.info(f"Jira API returned empty for {user.email or user.full_name}, falling back to full_name {user.full_name}")
                    params = {"query": user.full_name}
                    response = requests.get(user_search_url, auth=jira_auth, params=params, timeout=10)
                
                if response.status_code == 200:
                    jira_users = response.json()
                    if jira_users:
                        jira_user = jira_users[0]
                        user.jira_account_id = jira_user.get("accountId")
                        db.commit()
                        logger.info(f"Discovered Jira accountId for {user.full_name}: {user.jira_account_id}")
                    else:
                        logger.warning(f"Jira API returned empty user list for search: {user.email or user.full_name}")
                        response = None # skip
                else:
                    logger.warning(f"Jira API search failed with status {response.status_code}: {response.text}")
                    response = None # skip
            else:
                user_url = f"{jira_url}/rest/api/3/user"
                response = requests.get(user_url, auth=jira_auth, params={"accountId": user.jira_account_id}, timeout=10)
                
            if response and response.status_code == 200:
                if isinstance(response.json(), list):
                    jira_user = response.json()[0]
                else:
                    jira_user = response.json()
                
                # Update or create identity
                jira_identity = db.query(models.EmployeeIdentity).filter(
                    and_(
                        models.EmployeeIdentity.user_id == user.id,
                        models.EmployeeIdentity.source == "jira",
                        models.EmployeeIdentity.external_user_id == user.jira_account_id
                    )
                ).first()
                
                identity_data = {
                    "user_id": user.id,
                    "source": "jira",
                    "external_user_id": user.jira_account_id,
                    "username": jira_user.get("name"),
                    "email": jira_user.get("emailAddress"),
                    "full_name": jira_user.get("displayName"),
                    "is_verified": True
                }
                
                if not jira_identity:
                    jira_identity = models.EmployeeIdentity(**identity_data)
                    db.add(jira_identity)
                else:
                    jira_identity.email = jira_user.get("emailAddress")
                    jira_identity.full_name = jira_user.get("displayName")
                    jira_identity.is_verified = True
                
                db.commit()
                
                identities["jira"] = {
                    "external_user_id": user.jira_account_id,
                    "username": jira_user.get("name"),
                    "email": jira_user.get("emailAddress"),
                    "verified": True
                }
                
                logger.info(f"Discovered Jira identity for {user.full_name}: {jira_user.get('name')}")
            elif response:
                logger.warning(f"Jira API user fetch failed for accountId {user.jira_account_id} with status {response.status_code}: {response.text}")
                
        except Exception as e:
            logger.error(f"Error discovering Jira identity for {user.full_name}: {str(e)}")
    
    return identities

# ─────────────────────────────────────────────────────────────
# GITLAB SYNC (SMART DISCOVERY ENGINE)
# ─────────────────────────────────────────────────────────────

def discover_all_gitlab_projects(db: Session, settings: models.IntegrationSetting) -> List[models.Project]:
    """
    Smart GitLab Discovery Engine:
    Crawls all groups, subgroups, user namespaces, and instance-wide projects on GitLab.
    Registers/updates every project in the SQLite 'projects' table.
    """
    if not settings.gitlab_url or not settings.gitlab_token_encrypted:
        return []
    
    gitlab_token = decrypt_val(settings.gitlab_token_encrypted)
    gitlab_url = settings.gitlab_url.rstrip("/")
    headers = {"PRIVATE-TOKEN": gitlab_token}
    
    discovered_projects = []
    seen_external_ids = set()
    
    # 1. Fetch all projects instance-wide with pagination
    page = 1
    while True:
        try:
            res = requests.get(
                f"{gitlab_url}/api/v4/projects",
                headers=headers,
                params={"all_available": True, "per_page": 100, "page": page},
                timeout=15
            )
            if res.status_code != 200:
                break
            batch = res.json()
            if not batch or not isinstance(batch, list):
                break
                
            for proj_data in batch:
                ext_id = str(proj_data.get("id"))
                if ext_id in seen_external_ids:
                    continue
                seen_external_ids.add(ext_id)
                
                # Full path with namespace (e.g. "promo/quota-management-bca", "falcon-v2/falcon-v2", "anang/falcon-mobile-version2")
                path_ns = proj_data.get("path_with_namespace") or proj_data.get("name")
                web_url = proj_data.get("web_url")
                
                existing = db.query(models.Project).filter(
                    and_(
                        models.Project.source == "gitlab",
                        models.Project.external_project_id == ext_id
                    )
                ).first()
                
                if not existing:
                    new_proj = models.Project(
                        source="gitlab",
                        external_project_id=ext_id,
                        project_name=path_ns,
                        project_url=web_url,
                        is_active=True
                    )
                    db.add(new_proj)
                    try:
                        db.commit()
                        db.refresh(new_proj)
                        discovered_projects.append(new_proj)
                    except Exception:
                        db.rollback()
                else:
                    if existing.project_name != path_ns:
                        existing.project_name = path_ns
                        try:
                            db.commit()
                        except Exception:
                            db.rollback()
                    discovered_projects.append(existing)
            
            page += 1
            if page > 20:  # Safety limit: max 2000 projects
                break
        except Exception as e:
            logger.error(f"Error in GitLab project discovery page {page}: {e}")
            break

    # 2. Fetch all groups and their subgroup projects
    try:
        res_groups = requests.get(
            f"{gitlab_url}/api/v4/groups",
            headers=headers,
            params={"all_available": True, "per_page": 100},
            timeout=15
        )
        if res_groups.status_code == 200:
            groups_data = res_groups.json()
            if isinstance(groups_data, list):
                for g in groups_data:
                    gid = g.get("id")
                    if not gid:
                        continue
                    res_gp = requests.get(
                        f"{gitlab_url}/api/v4/groups/{gid}/projects",
                        headers=headers,
                        params={"include_subgroups": True, "per_page": 100},
                        timeout=15
                    )
                    if res_gp.status_code == 200:
                        g_projs = res_gp.json()
                        if isinstance(g_projs, list):
                            for proj_data in g_projs:
                                ext_id = str(proj_data.get("id"))
                                if ext_id in seen_external_ids:
                                    continue
                                seen_external_ids.add(ext_id)
                                
                                path_ns = proj_data.get("path_with_namespace") or proj_data.get("name")
                                web_url = proj_data.get("web_url")
                                
                                existing = db.query(models.Project).filter(
                                    and_(
                                        models.Project.source == "gitlab",
                                        models.Project.external_project_id == ext_id
                                    )
                                ).first()
                                if not existing:
                                    new_proj = models.Project(
                                        source="gitlab",
                                        external_project_id=ext_id,
                                        project_name=path_ns,
                                        project_url=web_url,
                                        is_active=True
                                    )
                                    db.add(new_proj)
                                    try:
                                        db.commit()
                                        db.refresh(new_proj)
                                        discovered_projects.append(new_proj)
                                    except Exception:
                                        db.rollback()
                                else:
                                    discovered_projects.append(existing)
    except Exception as e:
        logger.error(f"Error discovering group projects: {e}")

    logger.info(f"Smart GitLab Discovery Engine registered {len(discovered_projects)} projects in DB.")
    return discovered_projects


def sync_gitlab_commits(db: Session, user: models.User, settings: models.IntegrationSetting, 
                       start_date: datetime, end_date: datetime) -> int:
    """Sync GitLab commits for a user across all discovered projects in the entire GitLab server"""
    
    gitlab_identity = db.query(models.EmployeeIdentity).filter(
        and_(
            models.EmployeeIdentity.user_id == user.id,
            models.EmployeeIdentity.source == "gitlab"
        )
    ).first()
    
    if not gitlab_identity:
        logger.warning(f"No GitLab identity found for {user.full_name}, skipping commits")
        return 0
    
    gitlab_token = decrypt_val(settings.gitlab_token_encrypted)
    gitlab_url = settings.gitlab_url.rstrip("/")
    headers = {"PRIVATE-TOKEN": gitlab_token}
    
    # 1. Run Smart Discovery to make sure all projects across all groups are in DB
    discover_all_gitlab_projects(db, settings)
    
    # 2. Get all active GitLab projects from DB
    all_projects = db.query(models.Project).filter(
        and_(
            models.Project.source == "gitlab",
            models.Project.is_active == True
        )
    ).all()
    
    commits_synced = 0
    
    # Formulate author search queries
    author_queries = set()
    if user.full_name:
        author_queries.add(user.full_name)
        first_name = user.full_name.split()[0]
        if len(first_name) > 2:
            author_queries.add(first_name)
    
    if gitlab_identity.full_name:
        author_queries.add(gitlab_identity.full_name)
        git_first = gitlab_identity.full_name.split()[0]
        if len(git_first) > 2:
            author_queries.add(git_first)
            
    if gitlab_identity.username:
        author_queries.add(gitlab_identity.username)
        
    if gitlab_identity.email:
        author_queries.add(gitlab_identity.email)
        
    if user.email:
        author_queries.add(user.email)
    
    try:
        start_date_str = start_date.strftime("%Y-%m-%dT00:00:00Z")
        end_date_str = end_date.strftime("%Y-%m-%dT23:59:59Z")
        
        tasks = []
        for project_obj in all_projects:
            for author_query in author_queries:
                tasks.append((project_obj.external_project_id, project_obj.id, author_query))
                
        project_commits_by_db_id = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            future_to_db_id = {
                executor.submit(fetch_project_commits, pid, author, gitlab_url, headers, start_date_str, end_date_str): pdbid
                for pid, pdbid, author in tasks
            }
            for future in concurrent.futures.as_completed(future_to_db_id):
                pdbid = future_to_db_id[future]
                if pdbid not in project_commits_by_db_id:
                    project_commits_by_db_id[pdbid] = []
                batch = future.result()
                if batch:
                    project_commits_by_db_id[pdbid].extend(batch)
        
        for project_obj in all_projects:
            project_id = project_obj.external_project_id
            project_db_id = project_obj.id
            
            project_commits = project_commits_by_db_id.get(project_db_id, [])
            
            # Deduplicate commits by id
            seen_commit_ids = set()
            unique_commits = []
            for c in project_commits:
                if c.get("id") not in seen_commit_ids:
                    seen_commit_ids.add(c.get("id"))
                    unique_commits.append(c)
            
            for commit in unique_commits:
                commit_id = commit.get("id")
                
                # Check if raw commit already exists
                existing_commit = db.query(models.RawGitLabCommit).filter(
                    models.RawGitLabCommit.external_commit_id == commit_id
                ).first()
                
                if not existing_commit:
                    committed_date_raw = commit.get("committed_date")
                    committed_dt = datetime.fromisoformat(committed_date_raw.replace("Z", "+00:00")) if committed_date_raw else datetime.now()
                    
                    new_commit = models.RawGitLabCommit(
                        external_commit_id=commit_id,
                        project_id=project_db_id,
                        author_email=commit.get("author_email"),
                        author_name=commit.get("author_name"),
                        committer_email=commit.get("committer_email"),
                        committer_name=commit.get("committer_name"),
                        committed_date=committed_dt,
                        message=commit.get("message"),
                        web_url=commit.get("web_url"),
                        raw_data=commit
                    )
                    db.add(new_commit)
                    try:
                        db.commit()
                        commits_synced += 1
                    except Exception:
                        db.rollback()
                    
                    # Create normalized activity
                    activity_date = committed_dt.date()
                    
                    activity = models.Activity(
                        user_id=user.id,
                        source="gitlab",
                        activity_type="commit",
                        project_id=project_db_id,
                        reference_id=commit_id,
                        activity_date=activity_date,
                        activity_at=committed_dt,
                        activity_metadata={
                            "message": commit.get("message"),
                            "web_url": commit.get("web_url"),
                            "author_name": commit.get("author_name")
                        }
                    )
                    
                    existing_activity = db.query(models.Activity).filter(
                        and_(
                            models.Activity.user_id == user.id,
                            models.Activity.source == "gitlab",
                            models.Activity.activity_type == "commit",
                            models.Activity.reference_id == commit_id
                        )
                    ).first()
                    
                    if not existing_activity:
                        db.add(activity)
                        try:
                            db.commit()
                        except Exception:
                            db.rollback()

        logger.info(f"Smart Discovery: Synced {commits_synced} new commits for {user.full_name}")
        
    except Exception as e:
        logger.error(f"Error syncing GitLab commits for {user.full_name}: {str(e)}")
        db.rollback()
    
    return commits_synced
    
    return commits_synced

def sync_gitlab_merge_requests(db: Session, user: models.User, settings: models.IntegrationSetting,
                              start_date: datetime, end_date: datetime) -> int:
    """Sync GitLab merge requests for a user within date range"""
    
    # Get user's GitLab identity
    gitlab_identity = db.query(models.EmployeeIdentity).filter(
        and_(
            models.EmployeeIdentity.user_id == user.id,
            models.EmployeeIdentity.source == "gitlab"
        )
    ).first()
    
    if not gitlab_identity:
        return 0
    
    gitlab_token = decrypt_val(settings.gitlab_token_encrypted)
    gitlab_url = settings.gitlab_url.rstrip("/")
    username = gitlab_identity.username
    
    mrs_synced = 0
    
    try:
        # Get merge requests - use updated_after to catch MRs merged in period
        start_iso = start_date.isoformat()
        end_iso = end_date.isoformat()
        
        mrs_url = f"{gitlab_url}/api/v4/merge_requests"
        mrs_params = {
            "author_username": username,
            "updated_after": start_iso,
            "updated_before": end_iso,
            "state": "all",
            "scope": "all",
            "per_page": 100
        }
        
        response = requests.get(mrs_url, headers={"PRIVATE-TOKEN": gitlab_token},
                            params=mrs_params, timeout=30)
        
        if response.status_code == 200:
            mrs = response.json()
            
            if mrs and len(mrs) > 0:
                logger.info(f"CONSOLE: GITLAB MR DATA STRUCTURE for {user.full_name}:\n{json.dumps(mrs[0], indent=2)}")
            
            for mr in mrs:
                mr_id = str(mr.get("id"))
                project_id = str(mr.get("project_id"))
                
                # Get project info
                project_url = f"{gitlab_url}/api/v4/projects/{project_id}"
                project_response = requests.get(project_url, headers={"PRIVATE-TOKEN": gitlab_token}, timeout=10)
                
                if project_response.status_code == 200:
                    project = project_response.json()
                    
                    # Ensure project exists
                    existing_project = db.query(models.Project).filter(
                        and_(
                            models.Project.source == "gitlab",
                            models.Project.external_project_id == project_id
                        )
                    ).first()
                    
                    if not existing_project:
                        project_obj = models.Project(
                            source="gitlab",
                            external_project_id=project_id,
                            project_name=project.get("name"),
                            project_url=project.get("web_url"),
                            is_active=True
                        )
                        db.add(project_obj)
                        db.commit()
                        db.refresh(project_obj)
                        project_db_id = project_obj.id
                    else:
                        project_db_id = existing_project.id
                    
                    # Store raw MR data
                    existing_mr = db.query(models.RawGitLabMergeRequest).filter(
                        and_(
                            models.RawGitLabMergeRequest.external_mr_id == mr_id,
                            models.RawGitLabMergeRequest.project_id == project_db_id
                        )
                    ).first()
                    
                    created_date = datetime.fromisoformat(mr.get("created_at").replace("Z", "+00:00"))
                    merged_date = None
                    if mr.get("merged_at"):
                        merged_date = datetime.fromisoformat(mr.get("merged_at").replace("Z", "+00:00"))
                    
                    mr_state = mr.get("state")  # opened, closed, merged
                    activity_type = "mr_merged" if mr_state == "merged" else "mr_created"
                    activity_date = merged_date if merged_date else created_date
                    
                    if not existing_mr:
                        new_mr = models.RawGitLabMergeRequest(
                            external_mr_id=mr_id,
                            project_id=project_db_id,
                            author_email=mr.get("author", {}).get("email"),
                            author_name=mr.get("author", {}).get("name"),
                            title=mr.get("title"),
                            description=mr.get("description"),
                            state=mr_state,
                            created_at=created_date,
                            updated_at=datetime.fromisoformat(mr.get("updated_at").replace("Z", "+00:00")),
                            merged_at=merged_date,
                            web_url=mr.get("web_url"),
                            raw_data=mr
                        )
                        db.add(new_mr)
                        try:
                            db.commit()
                            mrs_synced += 1
                        except Exception:
                            db.rollback()
                    
                    # Create normalized activity
                    activity = models.Activity(
                        user_id=user.id,
                        source="gitlab",
                        activity_type=activity_type,
                        project_id=project_db_id,
                        reference_id=mr_id,
                        activity_date=activity_date.date(),
                        activity_at=activity_date,
                        activity_metadata={
                            "title": mr.get("title"),
                            "state": mr_state,
                            "web_url": mr.get("web_url")
                        }
                    )
                    
                    # Check for existing activity
                    existing_activity = db.query(models.Activity).filter(
                        and_(
                            models.Activity.user_id == user.id,
                            models.Activity.source == "gitlab",
                            models.Activity.reference_id == mr_id
                        )
                    ).first()
                    
                    if not existing_activity:
                        db.add(activity)
                        try:
                            db.commit()
                        except Exception:
                            db.rollback()
            
            db.commit()
            logger.info(f"Synced {mrs_synced} new merge requests for {user.full_name}")
    
    except Exception as e:
        logger.error(f"Error syncing GitLab MRs for {user.full_name}: {str(e)}")
        db.rollback()
    
    return mrs_synced

# ─────────────────────────────────────────────────────────────
# JIRA SYNC
# ─────────────────────────────────────────────────────────────

def sync_jira_issues(db: Session, user: models.User, settings: models.IntegrationSetting,
                     start_date: datetime, end_date: datetime) -> int:
    """Sync Jira issues (story points, completed issues) for a user within date range across all Jira projects"""
    
    jira_identity = db.query(models.EmployeeIdentity).filter(
        and_(
            models.EmployeeIdentity.user_id == user.id,
            models.EmployeeIdentity.source == "jira"
        )
    ).first()
    
    if not jira_identity:
        return 0
    
    jira_token = decrypt_val(settings.jira_token_encrypted)
    jira_auth = (settings.jira_email, jira_token)
    jira_url = settings.jira_url.rstrip("/")
    account_id = jira_identity.external_user_id
    
    issues_synced = 0
    
    try:
        search_url = f"{jira_url}/rest/api/3/search/jql"
        
        # JQL: query all issues assigned to user updated in the period or with completed status
        jql = f'assignee = "{account_id}" AND updated >= "{start_date.date()}" AND updated <= "{end_date.date()}"'
        
        next_page_token = None
        max_results = 100
        
        while True:
            payload = {
                "jql": jql,
                "fields": [
                    "summary", "description", "subtasks", "status", "project", 
                    "issuetype", "priority", "story_points", "customfield_10024", 
                    "customfield_10016", "customfield_10028", "resolutiondate", 
                    "created", "updated"
                ],
                "maxResults": max_results
            }
            if next_page_token:
                payload["nextPageToken"] = next_page_token
            
            response = requests.post(search_url, auth=jira_auth, json=payload, timeout=30)
            
            logger.info(f"DEBUG JIRA API for {user.full_name}: URL={response.url} STATUS={response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"DEBUG JIRA API RESPONSE for {user.full_name}: total={data.get('total')}, len(issues)={len(data.get('issues', []))}, raw={str(data)[:500]}")
                issues = data.get("issues", [])
                
                if issues and len(issues) > 0 and not next_page_token:
                    logger.info(f"CONSOLE: JIRA ISSUE DISCOVERY for {user.full_name}: first page fetched.")
                
                if not issues:
                    logger.info(f"Synced {issues_synced} new Jira issues (0 processed) for {user.full_name}")
                    break
                
                for issue in issues:
                    issue_key = issue.get("key")
                    fields = issue.get("fields", {})
                    
                    # Try custom fields for story points (including customfield_10024 used in Cloud)
                    raw_sp = fields.get("customfield_10024") or fields.get("customfield_10016") or fields.get("customfield_10028") or fields.get("story_points") or 0
                    try:
                        story_points = float(raw_sp) if raw_sp is not None else 0.0
                    except Exception:
                        story_points = 0.0
                
                    # Calculate feature weight (complexity score from issue type & priority)
                    feature_weight = calculate_feature_weight(issue)
                
                    # Final story points for KPI calculation (max of explicit SP vs feature weight)
                    effective_sp = story_points if story_points > 0 else feature_weight
                
                    # Map Jira project to DB Project record
                    proj_info = fields.get("project", {})
                    proj_key = proj_info.get("key", "") if proj_info else ""
                    proj_name = proj_info.get("name", "") if proj_info else ""
                
                    project_db_id = None
                    if proj_key:
                        existing_proj = db.query(models.Project).filter(
                            or_(
                                models.Project.project_name.ilike(f"%{proj_key}%"),
                                models.Project.project_key == proj_key
                            )
                        ).first()
                        if existing_proj:
                            project_db_id = existing_proj.id
                        else:
                            new_proj = models.Project(
                                project_name=proj_name or proj_key,
                                project_key=proj_key,
                                source="jira"
                            )
                            db.add(new_proj)
                            db.commit()
                            project_db_id = new_proj.id
                
                    # Store or update raw Jira issue
                    existing_issue = db.query(models.RawJiraIssue).filter(
                        models.RawJiraIssue.issue_key == issue_key
                    ).first()
                
                    resolution_date_str = fields.get("resolutiondate")
                    resolved_at = None
                    if resolution_date_str:
                        try:
                            resolved_at = datetime.strptime(resolution_date_str[:19], "%Y-%m-%dT%H:%M:%S")
                        except Exception:
                            resolved_at = datetime.now()
                    elif fields.get("updated"):
                        try:
                            resolved_at = datetime.strptime(fields.get("updated")[:19], "%Y-%m-%dT%H:%M:%S")
                        except Exception:
                            resolved_at = datetime.now()
                
                    if not existing_issue:
                        new_issue = models.RawJiraIssue(
                            issue_key=issue_key,
                            summary=fields.get("summary"),
                            issue_type=fields.get("issuetype", {}).get("name") if fields.get("issuetype") else None,
                            status=fields.get("status", {}).get("name") if fields.get("status") else None,
                            assignee_account_id=account_id,
                            story_points=effective_sp,
                            resolved_date=resolved_at,
                            raw_data=issue
                        )
                        db.add(new_issue)
                        try:
                            db.commit()
                            issues_synced += 1
                        except Exception as e:
                            db.rollback()
                    else:
                        existing_issue.story_points = effective_sp
                        existing_issue.status = fields.get("status", {}).get("name") if fields.get("status") else None
                        try:
                            db.commit()
                        except Exception as e:
                            db.rollback()
                
                    # Create or update activity for issue
                    existing_activity = db.query(models.Activity).filter(
                        and_(
                            models.Activity.user_id == user.id,
                            models.Activity.source == "jira",
                            models.Activity.activity_type == "issue_completed",
                            models.Activity.reference_id == issue_key
                        )
                    ).first()
                
                    status_cat = fields.get("status", {}).get("statusCategory", {}).get("name", "") if fields.get("status") else ""
                    status_name = fields.get("status", {}).get("name", "") if fields.get("status") else ""
                
                    if not existing_activity:
                        activity = models.Activity(
                            user_id=user.id,
                            source="jira",
                            activity_type="issue_completed",
                            reference_id=issue_key,
                            project_id=project_db_id,
                            activity_date=resolved_at.date() if hasattr(resolved_at, 'date') else datetime.now().date(),
                            activity_at=resolved_at if resolved_at else datetime.now(),
                            story_points=effective_sp,
                            activity_metadata={
                                "issue_key": issue_key,
                                "issue_summary": fields.get("summary"),
                                "story_points": story_points,
                                "feature_weight": feature_weight,
                                "effective_sp": effective_sp,
                                "jira_project_key": proj_key,
                                "jira_project_name": proj_name,
                                "status": status_name,
                                "status_category": status_cat
                            }
                        )
                        db.add(activity)
                        try:
                            db.commit()
                        except Exception as e:
                            db.rollback()
                    else:
                        existing_activity.story_points = effective_sp
                        if project_db_id and not existing_activity.project_id:
                            existing_activity.project_id = project_db_id
                        try:
                            db.commit()
                        except Exception:
                            db.rollback()
                
                logger.info(f"Synced {issues_synced} new Jira issues ({len(issues)} processed) for {user.full_name}")
                
                next_page_token = data.get('nextPageToken')
                if not next_page_token or data.get('isLast') is True:
                    break
            
            else:
                logger.error(f"Failed to fetch Jira issues for {user.full_name}: {response.status_code} {response.text}")
                break
                

    except Exception as e:
        logger.error(f"Error syncing Jira issues for {user.full_name}: {str(e)}")
        db.rollback()
    
    return issues_synced


def sync_jira_worklogs(db: Session, user: models.User, settings: models.IntegrationSetting,
                       start_date: datetime, end_date: datetime) -> int:
    """Sync Jira worklogs for a user within date range"""
    
    # Get user's Jira identity
    jira_identity = db.query(models.EmployeeIdentity).filter(
        and_(
            models.EmployeeIdentity.user_id == user.id,
            models.EmployeeIdentity.source == "jira"
        )
    ).first()
    
    if not jira_identity:
        return 0
    
    jira_token = decrypt_val(settings.jira_token_encrypted)
    jira_auth = (settings.jira_email, jira_token)
    jira_url = settings.jira_url.rstrip("/")
    account_id = jira_identity.external_user_id
    
    worklogs_synced = 0
    
    try:
        # Use /rest/api/3/search/jql endpoint (new Atlassian migration)
        search_url = f"{jira_url}/rest/api/3/search/jql"
        
        # JQL to find issues the user has logged work on
        jql = f'worklogAuthor = "{account_id}" AND worklogDate >= "{start_date.date()}" AND worklogDate <= "{end_date.date()}"'
        
        payload = {
            "jql": jql,
            "fields": ["worklog", "summary"],
            "maxResults": 100
        }
        
        response = requests.post(search_url, auth=jira_auth, json=payload, timeout=30)
        
        if response.status_code == 200:
            issues_data = response.json()
            issues = issues_data.get("issues", [])
            
            for issue in issues:
                issue_key = issue.get("key")
                worklog = issue.get("fields", {}).get("worklog")
                
                if worklog:
                    worklogs = worklog.get("worklogs", [])
                    
                    for wl in worklogs:
                        worklog_id = str(wl.get("id"))
                        author = wl.get("author", {}).get("accountId")
                        
                        if str(author) == account_id:
                            started = datetime.fromisoformat(wl.get("started").replace("Z", "+00:00"))
                            time_spent = wl.get("timeSpentSeconds", 0)
                            
                            # Store raw worklog data
                            existing_worklog = db.query(models.RawJiraWorklog).filter(
                                models.RawJiraWorklog.external_worklog_id == worklog_id
                            ).first()
                            
                            if not existing_worklog:
                                new_worklog = models.RawJiraWorklog(
                                    external_worklog_id=worklog_id,
                                    issue_key=issue_key,
                                    account_id=account_id,
                                    started=started,
                                    time_spent_seconds=time_spent,
                                    raw_data=wl
                                )
                                db.add(new_worklog)
                                try:
                                    db.commit()
                                    worklogs_synced += 1
                                except Exception:
                                    db.rollback()
                            
                            # Create normalized activity
                            activity = models.Activity(
                                user_id=user.id,
                                source="jira",
                                activity_type="worklog",
                                reference_id=worklog_id,
                                activity_date=started.date(),
                                activity_at=started,
                                duration_seconds=time_spent,
                                activity_metadata={
                                    "issue_key": issue_key,
                                    "issue_summary": issue.get("fields", {}).get("summary")
                                }
                            )
                            
                            # Check for existing activity
                            existing_activity = db.query(models.Activity).filter(
                                and_(
                                    models.Activity.user_id == user.id,
                                    models.Activity.source == "jira",
                                    models.Activity.activity_type == "worklog",
                                    models.Activity.reference_id == worklog_id
                                )
                            ).first()
                            
                            if not existing_activity:
                                db.add(activity)
                                try:
                                    db.commit()
                                except Exception:
                                    db.rollback()
            
            logger.info(f"Synced {worklogs_synced} new worklogs for {user.full_name}")
        else:
            logger.error(f"Failed to fetch worklogs for {user.full_name}: {response.status_code} {response.text}")
    
    except Exception as e:
        logger.error(f"Error syncing Jira worklogs for {user.full_name}: {str(e)}")
        db.rollback()
    
    return worklogs_synced

# ─────────────────────────────────────────────────────────────
# INCREMENTAL SYNC STATE MANAGEMENT
# ─────────────────────────────────────────────────────────────

def update_sync_state(db: Session, source: str, entity: str, last_cursor: str, 
                      status: str = "SUCCESS", error_message: str = None):
    """Update sync state for incremental synchronization"""
    
    sync_state = db.query(models.SyncState).filter(
        and_(
            models.SyncState.source == source,
            models.SyncState.entity == entity
        )
    ).first()
    
    current_time = datetime.now()
    
    if not sync_state:
        sync_state = models.SyncState(
            source=source,
            entity=entity,
            last_cursor=last_cursor,
            last_sync_at=current_time,
            status=status,
            error_message=error_message
        )
        db.add(sync_state)
    else:
        sync_state.last_cursor = last_cursor
        sync_state.last_sync_at = current_time
        sync_state.status = status
        if status == "ERROR":
            sync_state.error_message = error_message
            sync_state.retry_count += 1
        else:
            sync_state.retry_count = 0
    
    db.commit()

def get_last_sync_cursor(db: Session, source: str, entity: str) -> Optional[str]:
    """Get last sync cursor for incremental synchronization"""
    
    sync_state = db.query(models.SyncState).filter(
        and_(
            models.SyncState.source == source,
            models.SyncState.entity == entity
        )
    ).first()
    
    if sync_state and sync_state.last_cursor:
        return sync_state.last_cursor
    
    return None

def log_sync_operation(db: Session, source: str, entity: str, operation: str,
                      started_at: datetime, finished_at: datetime, status: str,
                      records_processed: int = 0, records_created: int = 0,
                      records_updated: int = 0, records_failed: int = 0,
                      error_message: str = None, sync_metadata: dict = None):
    """Log sync operation details"""
    
    log = models.SyncLog(
        source=source,
        entity=entity,
        operation=operation,
        started_at=started_at,
        finished_at=finished_at,
        status=status,
        records_processed=records_processed,
        records_created=records_created,
        records_updated=records_updated,
        records_failed=records_failed,
        error_message=error_message,
        sync_metadata=sync_metadata or {}
    )
    
    db.add(log)
    db.commit()

# ─────────────────────────────────────────────────────────────
# COMPREHENSIVE USER SYNC
# ─────────────────────────────────────────────────────────────

def sync_user_comprehensive(db: Session, user: models.User, settings: models.IntegrationSetting,
                            start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """
    Comprehensive sync for a user across all systems and all data types
    Follows the documentation's multi-project approach
    """
    
    started_at = datetime.now()
    total_records = 0
    
    try:
        # Step 1: Discover identities
        identities = discover_user_identities(db, user, settings)
        
        # Step 2: Sync GitLab data
        if identities.get("gitlab"):
            commits = sync_gitlab_commits(db, user, settings, start_date, end_date)
            mrs = sync_gitlab_merge_requests(db, user, settings, start_date, end_date)
            total_records += commits + mrs
        
        # Step 3: Sync Jira data
        if identities.get("jira"):
            jira_issues = sync_jira_issues(db, user, settings, start_date, end_date)
            worklogs = sync_jira_worklogs(db, user, settings, start_date, end_date)
            total_records += jira_issues + worklogs
        
        finished_at = datetime.now()
        
        # Log sync operation
        log_sync_operation(
            db=db,
            source="comprehensive",
            entity=f"user_{user.id}",
            operation="full_sync",
            started_at=started_at,
            finished_at=finished_at,
            status="SUCCESS",
            records_processed=total_records,
            records_created=total_records,
            sync_metadata={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "identities": list(identities.keys())
            }
        )
        
        # Update sync state
        update_sync_state(
            db=db,
            source="comprehensive",
            entity=f"user_{user.id}",
            last_cursor=end_date.isoformat(),
            status="SUCCESS"
        )
        
        return {
            "status": "success",
            "user_id": user.id,
            "user_name": user.full_name,
            "identities_discovered": len(identities),
            "total_records": total_records,
            "duration_seconds": (finished_at - started_at).total_seconds()
        }
        
    except Exception as e:
        finished_at = datetime.now()
        error_msg = str(e)
        
        logger.error(f"Comprehensive sync failed for {user.full_name}: {error_msg}")
        
        # Log failed operation
        log_sync_operation(
            db=db,
            source="comprehensive",
            entity=f"user_{user.id}",
            operation="full_sync",
            started_at=started_at,
            finished_at=finished_at,
            status="FAILED",
            records_processed=0,
            error_message=error_msg
        )
        
        # Update sync state with error
        update_sync_state(
            db=db,
            source="comprehensive",
            entity=f"user_{user.id}",
            last_cursor=start_date.isoformat(),
            status="ERROR",
            error_message=error_msg
        )
        
        return {
            "status": "error",
            "user_id": user.id,
            "user_name": user.full_name,
            "error": error_msg,
            "duration_seconds": (finished_at - started_at).total_seconds()
        }

# ─────────────────────────────────────────────────────────────
# AGGREGATED KPI CALCULATION
# ─────────────────────────────────────────────────────────────

def calculate_daily_aggregated_kpi(db: Session, user: models.User, date: datetime) -> Dict[str, Any]:
    """
    Calculate KPI aggregation for a specific date
    This follows the documentation's kpi_employee_daily approach
    """
    
    date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Get activities for this date
    activities = db.query(models.Activity).filter(
        and_(
            models.Activity.user_id == user.id,
            models.Activity.activity_date >= date_start,
            models.Activity.activity_date <= date_end
        )
    ).all()
    
    # Initialize metrics
    gitlab_commits = 0
    gitlab_mrs_created = 0
    gitlab_mrs_merged = 0
    jira_worklog_minutes = 0
    jira_issues_completed = 0
    jira_story_points = 0.0
    
    # Process activities
    for activity in activities:
        if activity.source == "gitlab":
            if activity.activity_type == "commit":
                gitlab_commits += 1
            elif activity.activity_type == "mr_created":
                gitlab_mrs_created += 1
            elif activity.activity_type in ["mr_merged", "merge_request"]:
                gitlab_mrs_merged += 1
        
        elif activity.source == "jira":
            if activity.activity_type == "worklog":
                if activity.duration_seconds:
                    jira_worklog_minutes += (activity.duration_seconds // 60)
            elif activity.activity_type in ["issue_done", "issue_completed"]:
                jira_issues_completed += 1
                # The seeder stores story points in activity_metadata
                sp = activity.story_points
                if not sp and activity.activity_metadata:
                    sp = activity.activity_metadata.get("story_points", 0)
                if sp:
                    jira_story_points += float(sp)
    
    # Get attendance for this date
    date_str = date.strftime("%Y-%m-%d")
    attendance = db.query(models.AttendanceRecord).filter(
        and_(
            models.AttendanceRecord.user_id == user.id,
            models.AttendanceRecord.date == date_str
        )
    ).first()
    
    if attendance:
        attendance_days = 1 if attendance.status in ["PRESENT", "LATE"] else 0
        late_count = 1 if attendance.is_late else 0
    else:
        # Fallback for years without explicit AttendanceRecord (e.g. 2025): default to 1 on working weekdays (Mon-Fri)
        # For 2026 onwards, we assume no record means absent.
        if date.year == 2025:
            attendance_days = 1 if date.weekday() < 5 else 0
        else:
            attendance_days = 0
        late_count = 0

    late_percentage = (late_count / attendance_days * 100) if attendance_days > 0 else 0.0
    
    # Calculate KPI scores based on current rules (simplified for now)
    # This would be enhanced with proper formula evaluation
    
    delivery_score = min((jira_issues_completed / 2.0) * 100, 120) if jira_issues_completed > 0 else 0.0
    engineering_score = min(((gitlab_commits + gitlab_mrs_merged) / 3.0) * 100, 120) if gitlab_commits > 0 else 0.0
    effort_score = min((jira_worklog_minutes / 480.0) * 100, 120) if jira_worklog_minutes > 0 else 0.0
    quality_score = 100.0  # Default value
    
    overall_score = (delivery_score * 0.3) + (engineering_score * 0.4) + (effort_score * 0.2) + (quality_score * 0.1)
    
    # Find relevant project and sprint
    relevant_sprint_id = None
    relevant_project_id = None
    
    if activities:
        latest_activity = max(activities, key=lambda x: x.activity_at)
        relevant_sprint_id = latest_activity.sprint_id
        relevant_project_id = latest_activity.project_id
    
    # Create or update daily KPI record
    daily_kpi = db.query(models.KPIEmployeeDaily).filter(
        and_(
            models.KPIEmployeeDaily.user_id == user.id,
            models.KPIEmployeeDaily.date == date_start
        )
    ).first()
    
    if not daily_kpi:
        daily_kpi = models.KPIEmployeeDaily(
            user_id=user.id,
            date=date_start,
            project_id=relevant_project_id,
            sprint_id=relevant_sprint_id,
            commit_count=gitlab_commits,
            mr_created=gitlab_mrs_created,
            mr_merged=gitlab_mrs_merged,
            mr_reviewed=0,
            issue_completed=jira_issues_completed,
            story_points_completed=jira_story_points,
            worklog_minutes=jira_worklog_minutes,
            bug_count=0,
            attendance_days=attendance_days,
            late_count=late_count,
            late_percentage=late_percentage,
            normal_percentage=100.0 - late_percentage,
            delivery_score=delivery_score,
            engineering_score=engineering_score,
            quality_score=quality_score,
            effort_score=effort_score,
            overall_score=overall_score,
            raw_activity_count=len(activities)
        )
        db.add(daily_kpi)
    else:
        # Update existing record
        daily_kpi.commit_count = gitlab_commits
        daily_kpi.mr_created = gitlab_mrs_created
        daily_kpi.mr_merged = gitlab_mrs_merged
        daily_kpi.issue_completed = jira_issues_completed
        daily_kpi.story_points_completed = jira_story_points
        daily_kpi.worklog_minutes = jira_worklog_minutes
        daily_kpi.attendance_days = attendance_days
        daily_kpi.late_count = late_count
        daily_kpi.late_percentage = late_percentage
        daily_kpi.normal_percentage = 100.0 - late_percentage
        daily_kpi.delivery_score = delivery_score
        daily_kpi.engineering_score = engineering_score
        daily_kpi.effort_score = effort_score
        daily_kpi.overall_score = overall_score
        daily_kpi.raw_activity_count = len(activities)
        daily_kpi.project_id = relevant_project_id
        daily_kpi.sprint_id = relevant_sprint_id
    
    db.commit()
    
    return {
        "date": date.strftime("%Y-%m-%d"),
        "user_id": user.id,
        "activities_count": len(activities),
        "overall_score": round(overall_score, 2),
        "delivery_score": round(delivery_score, 2),
        "engineering_score": round(engineering_score, 2),
        "effort_score": round(effort_score, 2),
        "quality_score": round(quality_score, 2),
        "gitlab_commits": gitlab_commits,
        "gitlab_mrs_merged": gitlab_mrs_merged,
        "jira_worklog_hours": round(jira_worklog_minutes / 60, 2),
        "jira_issues_completed": jira_issues_completed
    }


