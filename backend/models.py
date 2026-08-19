import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, Numeric, DateTime, JSON, Integer, Text, Float, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Division(Base):
    __tablename__ = "divisions"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    
    users = relationship("User", back_populates="division")
    kpi_rules = relationship("KPIRule", back_populates="division")

class User(Base):
    __tablename__ = "users"

    id = Column(String(50), primary_key=True)  # Store external user_id, e.g. "482"
    nik = Column(String(50), unique=True, nullable=False)
    employee_id = Column(String(50), nullable=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=True)
    jira_account_id = Column(String(100), nullable=True)
    gitlab_username = Column(String(100), nullable=True)
    roles = Column(JSON, default=[])  # e.g., ["MANAGER", "ROLE_ADMIN"]
    has_subordinates = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Multiple project/board assignments
    jira_board_ids = Column(JSON, default=[])  # List of Jira board IDs user is assigned to
    current_active_board = Column(String(50), nullable=True)  # Current active board ID
    
    division_id = Column(String(50), ForeignKey("divisions.id"), nullable=True)
    group_id = Column(String(50), nullable=True)
    group_name = Column(String(150), nullable=True)
    supervisor_id = Column(String(50), ForeignKey("users.id"), nullable=True)

    division = relationship("Division", back_populates="users")
    supervisor = relationship("User", remote_side=[id], backref="subordinates")
    raw_metrics = relationship("RawMetricsData", back_populates="user")
    kpi_scores = relationship("SprintKPIScore", back_populates="user")
    identities = relationship("EmployeeIdentity", back_populates="user")
    activities = relationship("Activity", back_populates="user")
    daily_kpi = relationship("KPIEmployeeDaily", back_populates="user")

class EmployeeIdentity(Base):
    """Identity mapping between HRIS, GitLab, and Jira"""
    __tablename__ = "employee_identity"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(20), nullable=False)  # "gitlab", "jira", "hris"
    external_user_id = Column(String(100), nullable=True)  # GitLab user ID, Jira account ID, HRIS ID
    username = Column(String(100), nullable=True)
    email = Column(String(150), nullable=True)
    full_name = Column(String(150), nullable=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="identities")

class Project(Base):
    """Projects from both GitLab and Jira"""
    __tablename__ = "projects"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    source = Column(String(20), nullable=False)  # "gitlab", "jira"
    external_project_id = Column(String(100), nullable=True)  # GitLab project ID, Jira project key
    project_name = Column(String(200), nullable=False)
    project_key = Column(String(50), nullable=True)  # Jira project key
    project_url = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    last_synced = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Sprint(Base):
    __tablename__ = "sprints"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    jira_sprint_id = Column(String(100), unique=True, nullable=True)
    jira_board_id = Column(String(50), nullable=True)  # Track which board this sprint belongs to
    sprint_name = Column(String(150), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(String(50), default="ACTIVE")  # ACTIVE, CLOSED, FUTURE
    sequence = Column(Integer, nullable=True)  # Sprint sequence number
    goal = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    raw_metrics = relationship("RawMetricsData", back_populates="sprint")
    kpi_scores = relationship("SprintKPIScore", back_populates="sprint")
    activities = relationship("Activity", back_populates="sprint")
    sprint_history = relationship("SprintHistory", back_populates="sprint")

class Issue(Base):
    """Issues from Jira"""
    __tablename__ = "issues"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    issue_key = Column(String(100), unique=True, nullable=False)  # Jira issue key like "PROJ-123"
    project_id = Column(String(50), ForeignKey("projects.id"), nullable=True)
    issue_type = Column(String(50), nullable=True)  # Story, Bug, Task, etc.
    summary = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=True)
    priority = Column(String(50), nullable=True)
    story_points = Column(Float, nullable=True)
    created_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    resolved_date = Column(DateTime, nullable=True)
    assignee_account_id = Column(String(100), nullable=True)
    reporter_account_id = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    last_synced = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    project = relationship("Project")
    activities = relationship("Activity", back_populates="issue")

# ─────────────────────────────────────────────────────────────
# SYNC STATE & LOGGING
# ─────────────────────────────────────────────────────────────

class SyncState(Base):
    """Track last sync position for incremental synchronization"""
    __tablename__ = "sync_state"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(20), nullable=False)  # "gitlab", "jira"
    entity = Column(String(50), nullable=False)  # "commits", "issues", "worklogs", etc.
    last_cursor = Column(String(500), nullable=True)  # Last synced cursor/timestamp
    last_sync_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="IDLE")  # IDLE, SYNCING, ERROR
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class SyncJob(Base):
    """Track background sync jobs for frontend polling"""
    __tablename__ = "sync_jobs"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    job_type = Column(String(50), nullable=False) # e.g., "KPI_SYNC", "ATTENDANCE_SYNC"
    status = Column(String(20), default="PENDING") # PENDING, RUNNING, COMPLETED, FAILED
    progress = Column(Integer, default=0) # 0 to 100
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class SyncLog(Base):
    """Detailed sync operation logs"""
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(20), nullable=False)
    entity = Column(String(50), nullable=False)
    operation = Column(String(20), nullable=False)  # "FETCH", "PROCESS", "STORE"
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="SUCCESS")  # SUCCESS, FAILED, PARTIAL
    records_processed = Column(Integer, default=0)
    records_created = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    sync_metadata = Column(JSON, default={})  # Renamed from metadata to avoid conflict
    created_at = Column(DateTime, default=func.now())

# ─────────────────────────────────────────────────────────────
# RAW DATA STORAGE (Original API Responses)
# ─────────────────────────────────────────────────────────────

class RawGitLabCommit(Base):
    """Raw GitLab commit data"""
    __tablename__ = "raw_gitlab_commits"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    external_commit_id = Column(String(100), unique=True, nullable=False)
    project_id = Column(String(50), nullable=True)
    author_email = Column(String(150), nullable=True)
    author_name = Column(String(150), nullable=True)
    committer_email = Column(String(150), nullable=True)
    committer_name = Column(String(150), nullable=True)
    committed_date = Column(DateTime, nullable=True)
    message = Column(Text, nullable=True)
    web_url = Column(String(500), nullable=True)
    raw_data = Column(JSON, default={})
    created_at = Column(DateTime, default=func.now())

class RawGitLabMergeRequest(Base):
    """Raw GitLab merge request data"""
    __tablename__ = "raw_gitlab_merge_requests"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    external_mr_id = Column(String(100), unique=True, nullable=False)
    project_id = Column(String(50), nullable=True)
    author_email = Column(String(150), nullable=True)
    author_name = Column(String(150), nullable=True)
    title = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    state = Column(String(50), nullable=True)  # opened, closed, merged
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    merged_at = Column(DateTime, nullable=True)
    web_url = Column(String(500), nullable=True)
    raw_data = Column(JSON, default={})
    created_at = Column(DateTime, default=func.now())

class RawGitLabEvent(Base):
    """Raw GitLab event data"""
    __tablename__ = "raw_gitlab_events"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    external_event_id = Column(String(100), unique=True, nullable=False)
    project_id = Column(String(50), nullable=True)
    user_email = Column(String(150), nullable=True)
    user_name = Column(String(150), nullable=True)
    action_type = Column(String(50), nullable=True)  # pushed, created, merged, etc.
    target_type = Column(String(50), nullable=True)  # commit, merge_request, issue
    target_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=True)
    raw_data = Column(JSON, default={})
    created_at = Column(DateTime, default=func.now())

class RawJiraIssue(Base):
    """Raw Jira issue data"""
    __tablename__ = "raw_jira_issues"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    issue_key = Column(String(100), unique=True, nullable=False)
    project_id = Column(String(50), nullable=True)
    issue_type = Column(String(50), nullable=True)
    summary = Column(Text, nullable=False)
    status = Column(String(50), nullable=True)
    priority = Column(String(50), nullable=True)
    story_points = Column(Float, nullable=True)
    assignee_account_id = Column(String(100), nullable=True)
    reporter_account_id = Column(String(100), nullable=True)
    created_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    resolved_date = Column(DateTime, nullable=True)
    # Precomputed multi-factor feature score (complexity_sp contribution).
    # Computed once at sync time by the FeatureScorer so request paths never re-scan.
    complexity_score = Column(Float, nullable=True)
    complexity_detail = Column(JSON, nullable=True)
    raw_data = Column(JSON, default={})
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())

class RawJiraWorklog(Base):
    """Raw Jira worklog data"""
    __tablename__ = "raw_jira_worklogs"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    external_worklog_id = Column(String(100), unique=True, nullable=False)
    issue_key = Column(String(100), nullable=False)
    account_id = Column(String(100), nullable=True)
    time_spent_seconds = Column(Integer, nullable=False)
    started = Column(DateTime, nullable=True)
    created_date = Column(DateTime, nullable=True)
    raw_data = Column(JSON, default={})
    created_at = Column(DateTime, default=func.now())

class RawJiraIssueHistory(Base):
    """Raw Jira issue change history"""
    __tablename__ = "raw_jira_issue_history"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    external_history_id = Column(String(100), unique=True, nullable=False)
    issue_key = Column(String(100), nullable=False)
    field = Column(String(50), nullable=False)  # status, assignee, sprint, etc.
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    changed_by = Column(String(100), nullable=True)
    created_date = Column(DateTime, nullable=False)
    raw_data = Column(JSON, default={})
    created_at = Column(DateTime, default=func.now())

# ─────────────────────────────────────────────────────────────
# HISTORICAL STATE TRACKING
# ─────────────────────────────────────────────────────────────

class IssueSprintHistory(Base):
    """Track sprint changes for issues over time"""
    __tablename__ = "issue_sprint_history"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    issue_id = Column(String(50), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False)
    sprint_id = Column(String(50), ForeignKey("sprints.id", ondelete="CASCADE"), nullable=True)
    valid_from = Column(DateTime, nullable=False)
    valid_to = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())

    issue = relationship("Issue")
    sprint = relationship("Sprint")

class SprintHistory(Base):
    """Track sprint changes over time"""
    __tablename__ = "sprint_history"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    sprint_id = Column(String(50), ForeignKey("sprints.id", ondelete="CASCADE"), nullable=False)
    field = Column(String(50), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    changed_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())

    sprint = relationship("Sprint", back_populates="sprint_history")

# ─────────────────────────────────────────────────────────────
# NORMALIZED ACTIVITY LAYER
# ─────────────────────────────────────────────────────────────

class Activity(Base):
    """Normalized activity from all sources"""
    __tablename__ = "activities"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(20), nullable=False)  # "gitlab", "jira"
    activity_type = Column(String(50), nullable=False)  # "commit", "mr_created", "mr_merged", "worklog", "issue_done", etc.
    project_id = Column(String(50), ForeignKey("projects.id"), nullable=True)
    sprint_id = Column(String(50), ForeignKey("sprints.id"), nullable=True)
    issue_id = Column(String(50), ForeignKey("issues.id"), nullable=True)
    reference_id = Column(String(100), nullable=True)  # GitLab commit ID, Jira worklog ID, etc.
    activity_date = Column(DateTime, nullable=False, index=True)
    activity_at = Column(DateTime, nullable=False)  # Precise timestamp
    duration_seconds = Column(Integer, nullable=True)  # For worklogs
    story_points = Column(Float, nullable=True)  # For completed issues
    activity_metadata = Column(JSON, default={})  # Renamed from metadata to avoid conflict
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="activities")
    project = relationship("Project")
    sprint = relationship("Sprint", back_populates="activities")
    issue = relationship("Issue", back_populates="activities")

# ─────────────────────────────────────────────────────────────
# KPI AGGREGATION LAYER
# ─────────────────────────────────────────────────────────────

class KPIEmployeeDaily(Base):
    """Pre-aggregated KPI data by employee and date"""
    __tablename__ = "kpi_employee_daily"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(DateTime, nullable=False, index=True)
    project_id = Column(String(50), ForeignKey("projects.id"), nullable=True)
    sprint_id = Column(String(50), ForeignKey("sprints.id"), nullable=True)
    
    # GitLab metrics
    commit_count = Column(Integer, default=0)
    mr_created = Column(Integer, default=0)
    mr_merged = Column(Integer, default=0)
    mr_reviewed = Column(Integer, default=0)
    
    # Jira metrics
    issue_created = Column(Integer, default=0)
    issue_completed = Column(Integer, default=0)
    story_points_completed = Column(Float, default=0.0)
    worklog_minutes = Column(Integer, default=0)
    bug_count = Column(Integer, default=0)
    
    # Attendance metrics
    attendance_days = Column(Integer, default=0)
    late_count = Column(Integer, default=0)
    late_percentage = Column(Float, default=0.0)
    normal_percentage = Column(Float, default=0.0)
    
    # Calculated KPI scores
    delivery_score = Column(Float, default=0.0)
    engineering_score = Column(Float, default=0.0)
    quality_score = Column(Float, default=0.0)
    effort_score = Column(Float, default=0.0)
    overall_score = Column(Float, default=0.0)
    
    kpi_breakdown = Column(JSON, default={})
    raw_activity_count = Column(Integer, default=0)
    calculated_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="daily_kpi")
    project = relationship("Project")
    sprint = relationship("Sprint")

# ─────────────────────────────────────────────────────────────
# EXISTING TABLES (Enhanced for compatibility)
# ─────────────────────────────────────────────────────────────

class KPIRule(Base):
    __tablename__ = "kpi_rules"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    division_id = Column(String(50), ForeignKey("divisions.id"), nullable=False)
    group_id = Column(String(50), nullable=True)
    group_name = Column(String(150), nullable=True)
    name = Column(String(150), nullable=False)
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    rule_type = Column(String(50), default="SPRINT_BASED")  # "SPRINT_BASED" or "TIME_RANGE_BASED"

    division = relationship("Division", back_populates="kpi_rules")
    metrics = relationship("KPIRuleMetric", back_populates="kpi_rule", cascade="all, delete-orphan")
    kpi_scores = relationship("SprintKPIScore", back_populates="kpi_rule")

class KPIRuleMetric(Base):
    __tablename__ = "kpi_rule_metrics"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    kpi_rule_id = Column(String(50), ForeignKey("kpi_rules.id", ondelete="CASCADE"), nullable=False)
    metric_key = Column(String(100), nullable=False)  # e.g., 'jira_sp', 'gitlab_mr'
    weight = Column(Numeric(5, 4), nullable=False)  # e.g., 0.40
    calc_type = Column(String(50), default="FORMULA")  # FORMULA, DIRECT
    formula_expression = Column(Text, nullable=False)
    variables = Column(JSON, default={})  # e.g., {"target_sp": 20}
    cap_score = Column(Numeric(5, 2), default=120.0)
    category = Column(String(50), default="DELIVERY")  # DELIVERY, ENGINEERING, QUALITY, EFFORT

    kpi_rule = relationship("KPIRule", back_populates="metrics")

class RawMetricsData(Base):
    """Legacy table for backward compatibility - will be replaced by activities"""
    __tablename__ = "raw_metrics_data"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sprint_id = Column(String(50), ForeignKey("sprints.id", ondelete="CASCADE"), nullable=False)
    metrics_payload = Column(JSON, default={})  # e.g. {"jira_sp": 22, "gitlab_mr_merged": 4}
    fetched_at = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="raw_metrics")
    sprint = relationship("Sprint", back_populates="raw_metrics")

class SprintKPIScore(Base):
    """Legacy table for backward compatibility - will be enhanced by KPIEmployeeDaily"""
    __tablename__ = "sprint_kpi_scores"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sprint_id = Column(String(50), ForeignKey("sprints.id", ondelete="CASCADE"), nullable=False)
    kpi_rule_id = Column(String(50), ForeignKey("kpi_rules.id"), nullable=False)
    final_score = Column(Numeric(5, 2), nullable=False)
    breakdown_details = Column(JSON, nullable=False)
    calculated_at = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="kpi_scores")
    sprint = relationship("Sprint", back_populates="kpi_scores")
    kpi_rule = relationship("KPIRule", back_populates="kpi_scores")

class IntegrationSetting(Base):
    __tablename__ = "integration_settings"

    id = Column(Integer, primary_key=True, index=True)
    jira_url = Column(String(200), nullable=True)
    jira_email = Column(String(100), nullable=True)
    jira_token_encrypted = Column(String(500), nullable=True)
    # Support multiple boards
    jira_board_ids = Column(JSON, default=[])  # List of board IDs to sync from
    default_jira_board_id = Column(String(50), default="")  # Default board for users without assignments
    jira_sp_field = Column(String(50), default="customfield_10016")

    @property
    def jira_board_id(self):
        return self.default_jira_board_id

    @jira_board_id.setter
    def jira_board_id(self, value):
        self.default_jira_board_id = value
    
    gitlab_url = Column(String(200), default="https://gitlab.com")
    gitlab_token_encrypted = Column(String(500), nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class JiraBoard(Base):
    """Track configured Jira boards"""
    __tablename__ = "jira_boards"

    id = Column(String(50), primary_key=True, default=lambda: str(generate_uuid()))
    jira_board_id = Column(String(50), unique=True, nullable=False)  # Jira board ID
    board_name = Column(String(200), nullable=False)
    board_type = Column(String(50), default="scrum")  # scrum, kanban, simple
    location = Column(String(200), nullable=True)  # Project/Location name
    is_active = Column(Boolean, default=True)
    last_synced = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())

class AttendanceRecord(Base):
    """Legacy attendance tracking - will be enhanced"""
    __tablename__ = "attendance_records"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sprint_id = Column(String(50), ForeignKey("sprints.id", ondelete="CASCADE"), nullable=False)
    date = Column(String(10), nullable=False)  # "2026-08-13"
    clock_in = Column(String(8), nullable=True)  # "08:45:00"
    clock_out = Column(String(8), nullable=True)  # "17:30:00"
    scheduled_in = Column(String(8), default="09:00:00")  # Jadwal masuk dari timesheet
    is_late = Column(Boolean, default=False)
    late_minutes = Column(Integer, default=0)
    status = Column(String(20), default="PRESENT")  # PRESENT, ABSENT, LATE, LEAVE
    source = Column(String(20), default="SYNCED")  # SYNCED, MANUAL
    created_at = Column(DateTime, default=func.now())

    user = relationship("User", backref="attendance_records")
    sprint = relationship("Sprint", backref="attendance_records")

class CompanyMaxima(Base):
    """Company/group-wide 5-pillar maxima per period (computed once at sync time).

    Replaces the request-time company scan so /yearly-performance is a cheap DB read.
    A row with group_id = NULL is the company-wide (global) benchmark; rows with a
    group_id hold the benchmark of the indicator matrix for that specific group.
    """
    __tablename__ = "company_maxima"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    year = Column(Integer, nullable=False, index=True)
    period = Column(String(20), nullable=False, default="YEARLY")  # YEARLY / SPRINT
    group_id = Column(String(50), nullable=True, index=True)  # NULL = company-wide
    division_id = Column(String(50), nullable=True)
    max_raw_sp = Column(Float, nullable=False, default=0.0)
    max_complexity_sp = Column(Float, nullable=False, default=0.0)
    max_issues_cnt = Column(Integer, nullable=False, default=0)
    max_founder_sp = Column(Float, nullable=False, default=0.0)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("year", "period", "group_id", name="uq_company_maxima_scope"),
    )

class UserYearlyMetrics(Base):
    """Precomputed per-user, per-year delivery aggregates.

    Computed once at sync time so request paths never scan raw tables.
    """
    __tablename__ = "user_yearly_metrics"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    year = Column(Integer, nullable=False, index=True)
    period = Column(String(20), nullable=False, default="YEARLY")
    raw_sp = Column(Float, nullable=False, default=0.0)
    complexity_sp = Column(Float, nullable=False, default=0.0)
    issues_completed = Column(Integer, nullable=False, default=0)
    founder_credit = Column(Float, nullable=False, default=0.0)
    # Highest resolved_date already folded into the totals above. NULL = not
    # accumulated yet (full recompute on next run). DateTime (not Date) so the
    # exact timestamp is kept and later increments never re-count those rows.
    last_processed_date = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User")
    __table_args__ = (UniqueConstraint("user_id", "year", "period", name="uq_user_yearly_metrics"),)

