import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, Numeric, DateTime, JSON, Integer, Text, Float
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
    issue_history = relationship("RawJiraIssueHistory", back_populates="issue")
    sprint_history = relationship("IssueSprintHistory", back_populates="issue")
    activities = relationship("Activity", back_populates="issue")
