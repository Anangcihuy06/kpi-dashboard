# KPI Dashboard - Technical Design Document

**Document Version:** 1.0  
**Date:** August 18, 2025  
**Author:** Development Team  
**Status:** Production Ready  
**Environment:** Railway (PostgreSQL) + Vercel (React Frontend)

---

## Executive Summary

The KPI Dashboard is a comprehensive performance management system that calculates and tracks employee Key Performance Indicators (KPIs) based on Jira issues and GitLab contributions. The system uses AI-powered complexity scoring via OpenRouter's GPT-4o-mini LLM to provide accurate, fair, and transparent performance metrics across multiple teams and divisions.

**Key Capabilities:**
- Real-time KPI calculation with AI-driven complexity scoring
- Multi-division support with configurable scoring rules
- Automatic synchronization with Jira and GitLab
- Webhook-based real-time updates (planned feature)
- Role-based access control and team hierarchy
- Comprehensive reporting and analytics

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Database Schema](#database-schema)
3. [Entity Relationships](#entity-relationships)
4. [Existing Services](#existing-services)
5. [Application Workflow](#application-workflow)
6. [KPI Calculation Mechanism](#kpi-calculation-mechanism)
7. [LLM Integration](#llm-integration)
8. [Multi-Team KPI Calculation](#multi-team-kpi-calculation)
9. [Jira Task Requirements](#jira-task-requirements)
10. [Technical Specifications](#technical-specifications)
11. [Deployment Architecture](#deployment-architecture)
12. [Security Considerations](#security-considerations)

---

## 1. System Architecture

### 1.1 Overall Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                            │
│                    React 19 + Vite (Vercel)                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │
│  │  Dashboard  │ │  Configurator │ │ Subordinates │ │ Reports      │  │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │ HTTPS
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer                                │
│                    FastAPI (Railway)                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │
│  │  Auth API   │ │  KPI API    │ │  Sync API   │ │ Admin API    │  │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │
│  │  User API   │ │ Board API   │ │ Job API     │ │ Webhook API  │  │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Business Logic Layer                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │
│  │ Sync Service│ │   Engine    │ │  Scheduler  │ │ Webhook Hdr │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │
│  │ Feature Ana│ │ Cache Mgr   │ │ Auth Mgr    │ │ Retry Logic  │  │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Data Access Layer                           │
│                    SQLAlchemy ORM                                │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │
│  │  User Repo  │ │ Issue Repo  │ │ KPI Repo    │ │ Config Repo  │  │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Data Storage Layer                          │
│                   PostgreSQL (Railway)                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │
│  │  Users      │ │  Issues     │ │  KPI Data   │ │ Configuration│ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      External Services                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │
│  │  Jira API   │ │  GitLab API │ │  HRIS API   │ │ OpenRouter   │  │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Technology Stack

#### Frontend
- **Framework:** React 19 + Vite
- **Deployment:** Vercel
- **URL:** https://kpi-dashboard-xi-murex.vercel.app
- **Key Libraries:** Axios, React Router, Chart.js

#### Backend
- **Framework:** FastAPI
- **Database:** PostgreSQL (Railway)
- **ORM:** SQLAlchemy
- **Deployment:** Railway
- **URL:** https://services-kpi-production.up.railway.app
- **Task Scheduling:** APScheduler
- **Caching:** FastAPICache (in-memory)

#### External Services
- **Jira:** Issue tracking and project management
- **GitLab:** Version control and merge requests
- **HRIS API:** User authentication and organizational data
- **OpenRouter:** LLM API for complexity scoring (GPT-4o-mini)

---

## 2. Database Schema

### 2.1 Core Tables

#### User Management
```sql
CREATE TABLE divisions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    division_id INTEGER REFERENCES divisions(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    position VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    division_id INTEGER REFERENCES divisions(id),
    group_id INTEGER REFERENCES groups(id),
    supervisor_id INTEGER REFERENCES users(id),
    employee_id VARCHAR(20) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Integration mappings
    jira_account_id VARCHAR(100),
    gitlab_username VARCHAR(100),
    jira_board_ids JSONB,
    current_active_board VARCHAR(50),
    
    INDEX idx_division_id (division_id),
    INDEX idx_group_id (group_id),
    INDEX idx_supervisor_id (supervisor_id),
    INDEX idx_jira_account_id (jira_account_id),
    INDEX idx_gitlab_username (gitlab_username)
);
```

#### Sprint Management
```sql
CREATE TABLE sprints (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    sprint_number INTEGER NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(name, sprint_number),
    INDEX idx_dates (start_date, end_date),
    INDEX idx_is_active (is_active)
);
```

#### KPI Rules & Metrics
```sql
CREATE TABLE kpi_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    rule_type VARCHAR(50) NOT NULL,
    formula TEXT,
    config_matrix JSONB NOT NULL,
    division_id INTEGER REFERENCES divisions(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_division_id (division_id),
    INDEX idx_rule_type (rule_type),
    INDEX idx_is_active (is_active)
);

CREATE TABLE kpi_rule_metrics (
    id SERIAL PRIMARY KEY,
    rule_id INTEGER REFERENCES kpi_rules(id) ON DELETE CASCADE,
    metric_name VARCHAR(100) NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    config_matrix JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_rule_id (rule_id),
    INDEX idx_metric_name (metric_name)
);
```

#### Raw Data Storage
```sql
CREATE TABLE raw_jira_issues (
    id SERIAL PRIMARY KEY,
    issue_key VARCHAR(50) UNIQUE NOT NULL,
    issue_id INTEGER,
    project_key VARCHAR(20),
    summary TEXT,
    description TEXT,
    status VARCHAR(50),
    issue_type VARCHAR(50),
    priority VARCHAR(50),
    assignee VARCHAR(100),
    reporter VARCHAR(100),
    created_date TIMESTAMP,
    updated_date TIMESTAMP,
    resolved_date TIMESTAMP,
    story_points DECIMAL(5,2),
    time_spent_seconds INTEGER,
    time_estimate_seconds INTEGER,
    
    -- Complexity scoring
    complexity_score DECIMAL(5,2),
    complexity_detail JSONB,
    score_type VARCHAR(20),
    model_used VARCHAR(50),
    scored_at TIMESTAMP,
    
    -- Group and division tracking
    group_id INTEGER,
    division_id INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_issue_key (issue_key),
    INDEX idx_project_key (project_key),
    INDEX idx_assignee (assignee),
    INDEX idx_status (status),
    INDEX idx_created_date (created_date),
    INDEX idx_division_id (division_id),
    INDEX idx_group_id (group_id),
    INDEX idx_complexity_score (complexity_score)
);

CREATE TABLE raw_gitlab_commits (
    id SERIAL PRIMARY KEY,
    commit_hash VARCHAR(100) UNIQUE NOT NULL,
    project_id INTEGER,
    project_name VARCHAR(200),
    author_name VARCHAR(100),
    author_email VARCHAR(100),
    commit_message TEXT,
    created_at TIMESTAMP,
    merged_at TIMESTAMP,
    issue_key VARCHAR(50),
    mr_id INTEGER,
    
    created_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_commit_hash (commit_hash),
    INDEX idx_issue_key (issue_key),
    INDEX idx_project_id (project_id),
    INDEX idx_author_email (author_email),
    INDEX idx_created_at (created_at)
);
```

#### Aggregated KPI Data
```sql
CREATE TABLE company_maxima (
    id SERIAL PRIMARY KEY,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    division_id INTEGER REFERENCES divisions(id),
    
    -- Maxima for complexity-based calculation
    max_raw_sp DECIMAL(10,2) DEFAULT 0,
    max_complexity_sp DECIMAL(10,2) DEFAULT 0,
    max_issues_cnt INTEGER DEFAULT 0,
    
    -- Maxima for component-based calculation
    max_c_sp DECIMAL(10,2) DEFAULT 0,
    max_i_sp DECIMAL(10,2) DEFAULT 0,
    max_s_sp DECIMAL(10,2) DEFAULT 0,
    max_r_sp DECIMAL(10,2) DEFAULT 0,
    max_o_sp DECIMAL(10,2) DEFAULT 0,
    
    -- Metadata
    record_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(period_start, period_end, division_id),
    INDEX idx_period (period_start, period_end),
    INDEX idx_division_id (division_id)
);

CREATE TABLE user_yearly_metrics (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    year INTEGER NOT NULL,
    division_id INTEGER REFERENCES divisions(id),
    
    -- Raw metrics
    total_raw_sp DECIMAL(10,2) DEFAULT 0,
    total_complexity_sp DECIMAL(10,2) DEFAULT 0,
    total_issues_cnt INTEGER DEFAULT 0,
    
    -- Component metrics
    total_c_sp DECIMAL(10,2) DEFAULT 0,
    total_i_sp DECIMAL(10,2) DEFAULT 0,
    total_s_sp DECIMAL(10,2) DEFAULT 0,
    total_r_sp DECIMAL(10,2) DEFAULT 0,
    total_o_sp DECIMAL(10,2) DEFAULT 0,
    
    -- Final scores
    final_percentage DECIMAL(5,2) DEFAULT 0,
    final_score DECIMAL(5,2) DEFAULT 0,
    
    -- Metadata
    issue_count INTEGER DEFAULT 0,
    record_count INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, year),
    INDEX idx_user_id (user_id),
    INDEX idx_year (year),
    INDEX idx_division_id (division_id)
);

CREATE TABLE kpi_employee_daily (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    sprint_id INTEGER REFERENCES sprints(id),
    sprint_number INTEGER,
    date DATE NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    
    -- Daily metrics
    daily_raw_sp DECIMAL(10,2) DEFAULT 0,
    daily_complexity_sp DECIMAL(10,2) DEFAULT 0,
    daily_issues_cnt INTEGER DEFAULT 0,
    daily_c_sp DECIMAL(10,2) DEFAULT 0,
    daily_i_sp DECIMAL(10,2) DEFAULT 0,
    daily_s_sp DECIMAL(10,2) DEFAULT 0,
    daily_r_sp DECIMAL(10,2) DEFAULT 0,
    daily_o_sp DECIMAL(10,2) DEFAULT 0,
    daily_merged_mr INTEGER DEFAULT 0,
    
    -- Running totals
    cumulative_raw_sp DECIMAL(10,2) DEFAULT 0,
    cumulative_complexity_sp DECIMAL(10,2) DEFAULT 0,
    cumulative_issues_cnt INTEGER DEFAULT 0,
    cumulative_c_sp DECIMAL(10,2) DEFAULT 0,
    cumulative_i_sp DECIMAL(10,2) DEFAULT 0,
    cumulative_s_sp DECIMAL(10,2) DEFAULT 0,
    cumulative_r_sp DECIMAL(10,2) DEFAULT 0,
    cumulative_o_sp DECIMAL(10,2) DEFAULT 0,
    cumulative_merged_mr INTEGER DEFAULT 0,
    
    -- Scores
    final_percentage DECIMAL(5,2) DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, sprint_id, date),
    INDEX idx_user_id (user_id),
    INDEX idx_sprint_id (sprint_id),
    INDEX idx_date (date),
    INDEX idx_year_month (year, month),
    INDEX idx_quarter (quarter)
);
```

#### Integration Settings
```sql
CREATE TABLE integration_settings (
    id SERIAL PRIMARY KEY,
    division_id INTEGER REFERENCES divisions(id),
    
    -- Jira settings
    jira_base_url VARCHAR(255),
    jira_token_encrypted TEXT,
    jira_email VARCHAR(100),
    jira_project_keys JSONB,
    jira_status_mapping JSONB,
    
    -- GitLab settings
    gitlab_base_url VARCHAR(255),
    gitlab_token_encrypted TEXT,
    gitlab_project_ids JSONB,
    
    -- Sync settings
    sync_enabled BOOLEAN DEFAULT TRUE,
    sync_interval_minutes INTEGER DEFAULT 60,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(division_id),
    INDEX idx_division_id (division_id)
);
```

#### Job Management
```sql
CREATE TABLE sync_jobs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(50) UNIQUE NOT NULL,
    job_type VARCHAR(50) NOT NULL,
    user_id INTEGER REFERENCES users(id),
    division_id INTEGER REFERENCES divisions(id),
    status VARCHAR(20) NOT NULL,
    progress INTEGER DEFAULT 0,
    total_items INTEGER DEFAULT 0,
    processed_items INTEGER DEFAULT 0,
    failed_items INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_job_id (job_id),
    INDEX idx_job_type (job_type),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_started_at (started_at)
);
```

### 2.2 Webhook Tables (Planned Feature)

```sql
CREATE TABLE webhook_configurations (
    id SERIAL PRIMARY KEY,
    division_id INTEGER REFERENCES divisions(id),
    jira_webhook_url VARCHAR(255),
    gitlab_webhook_url VARCHAR(255),
    enabled_events JSONB,
    retry_config JSONB,
    webhook_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(division_id),
    INDEX idx_division_id (division_id)
);

CREATE TABLE webhook_secrets (
    id SERIAL PRIMARY KEY,
    webhook_config_id INTEGER REFERENCES webhook_configurations(id),
    service_type VARCHAR(20) NOT NULL,
    encrypted_secret TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_webhook_config_id (webhook_config_id),
    INDEX idx_service_type (service_type)
);

CREATE TABLE webhook_ip_whitelist (
    id SERIAL PRIMARY KEY,
    webhook_config_id INTEGER REFERENCES webhook_configurations(id),
    ip_address VARCHAR(45) NOT NULL,
    allowed BOOLEAN DEFAULT TRUE,
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_webhook_config_id (webhook_config_id),
    INDEX idx_ip_address (ip_address)
);

CREATE TABLE raw_jira_issue_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(100) UNIQUE NOT NULL,
    issue_key VARCHAR(50),
    webhook_event_type VARCHAR(50),
    payload JSONB,
    processed BOOLEAN DEFAULT FALSE,
    processing_status VARCHAR(20),
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    
    INDEX idx_event_id (event_id),
    INDEX idx_issue_key (issue_key),
    INDEX idx_processed (processed),
    INDEX idx_created_at (created_at)
);

CREATE TABLE raw_gitlab_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(100) UNIQUE NOT NULL,
    project_id INTEGER,
    mr_id INTEGER,
    webhook_event_type VARCHAR(50),
    payload JSONB,
    processed BOOLEAN DEFAULT FALSE,
    processing_status VARCHAR(20),
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    
    INDEX idx_event_id (event_id),
    INDEX idx_project_id (project_id),
    INDEX idx_processed (processed),
    INDEX idx_created_at (created_at)
);
```

---

## 3. Entity Relationships

### 3.1 Entity Relationship Diagram

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│    divisions    │─────────│      groups     │─────────│      users      │
│  (id, name)     │ 1:N     │  (id, name)     │ 1:N     │  (id, email)    │
└─────────────────┘         └─────────────────┘         └────────┬────────┘
                                                                  │
                                          ┌───────────────────────┼───────────────────────┐
                                          │                       │                       │
                                          ▼                       ▼                       ▼
                                ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
                                │ raw_jira_issues │     │  kpi_employee   │     │   sync_jobs     │
                                │  (issue_key)    │     │     _daily      │     │  (job_id)       │
                                └─────────────────┘     └─────────────────┘     └─────────────────┘
                                          │                       │
                                          │                       │
                                          ▼                       ▼
                                ┌─────────────────┐     ┌─────────────────┐
                                │company_maxima   │     │user_yearly_     │
                                │(period_start)   │     │metrics          │
                                └─────────────────┘     └─────────────────┘
                                        
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│    kpi_rules    │─────────│ kpi_rule_       │─────────│ integration_    │
│  (id, name)     │ 1:N     │ metrics         │ 1:1     │ settings        │
└─────────────────┘         │(rule_id,metric) │         │(division_id)    │
                            └─────────────────┘         └─────────────────┘
                                                                 │
                                                                 │
                                                                 ▼
                                                       ┌─────────────────┐
                                                       │webhook_         │
                                                       │configurations   │
                                                       └────────┬────────┘
                                                                │
                                           ┌────────────────────┼────────────────────┐
                                           │                    │                    │
                                           ▼                    ▼                    ▼
                                   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
                                   │webhook_      │   │webhook_      │   │webhook_      │
                                   │secrets       │   │ip_whitelist  │   │raw_jira_     │
                                   │(service_type)│   │(ip_address)  │   │issue_events  │
                                   └──────────────┘   └──────────────┘   └──────────────┘
```

### 3.2 Relationship Descriptions

#### User Management
- **divisions → groups**: One-to-Many (One division has multiple groups)
- **groups → users**: One-to-Many (One group has multiple users)
- **users → users**: Self-referential (supervisor_id refers to another user)
- **divisions → users**: One-to-Many (One division has multiple users)

#### Data Collection
- **users → raw_jira_issues**: One-to-Many (One user has multiple issues via assignee)
- **users → kpi_employee_daily**: One-to-Many (One user has daily records)
- **sprints → kpi_employee_daily**: One-to-Many (One sprint has daily records)
- **users → sync_jobs**: One-to-Many (One user has sync jobs)

#### KPI Calculation
- **raw_jira_issues → company_maxima**: Many-to-One (Issues contribute to company maxima)
- **users → user_yearly_metrics**: One-to-One (One user has yearly metrics per year)
- **kpi_employee_daily → user_yearly_metrics**: Many-to-One (Daily records aggregate to yearly)

#### Configuration
- **divisions → kpi_rules**: One-to-Many (One division has multiple KPI rules)
- **kpi_rules → kpi_rule_metrics**: One-to-Many (One rule has multiple metrics)
- **divisions → integration_settings**: One-to-One (One division has integration settings)

#### Webhooks (Planned)
- **webhook_configurations → webhook_secrets**: One-to-Many (One config has multiple secrets)
- **webhook_configurations → webhook_ip_whitelist**: One-to-Many (One config has multiple IPs)
- **webhook_configurations → raw_jira_issue_events**: One-to-Many (One config receives events)
- **webhook_configurations → raw_gitlab_events**: One-to-Many (One config receives events)

---

## 4. Existing Services

### 4.1 Authentication Service (`main.py`)

**Endpoints:**
- `POST /api/v1/auth/login` - Authenticate via HRIS API
- `GET /api/v1/auth/verify` - Verify token validity
- `GET /api/v1/auth/me` - Get current user info

**Functionality:**
- External HRIS API authentication (`https://hris-api.atibusinessgroup.com`)
- Session-based token management
- User profile synchronization on first login
- Supervisor-subordinate relationship sync

**Key Functions:**
```python
async def login(username: str, password: str)
async def verify_token(token: str)
async def get_current_user(db: Session, token: str)
```

### 4.2 KPI Calculation Service (`engine.py`)

**Purpose:** Safe mathematical expression evaluation for KPI formulas

**Key Classes:**
```python
class SafeMathEvaluator:
    def __init__(self, max_operations=100)
    def evaluate(self, expression: str, variables: dict) -> float
    def get_evaluation_stats(self) -> dict
```

**Supported Operations:**
- Arithmetic: `+`, `-`, `*`, `/`, `%`, `**`
- Comparison: `==`, `!=`, `<`, `<=`, `>`, `>=`
- Logical: `and`, `or`, `not`
- Functions: `abs()`, `round()`, `min()`, `max()`, `sum()`

**Security Features:**
- AST-based parsing (no `eval()`)
- Operation count limits
- Invalid operation detection
- Type checking

### 4.3 Sync Service (`comprehensive_sync.py`)

**Purpose:** Comprehensive user synchronization with Jira and GitLab

**Key Functions:**
```python
def sync_user_comprehensive(
    db: Session,
    user: User,
    settings: IntegrationSetting,
    start_date: datetime,
    end_date: datetime,
    force_update: bool = False
)

def calculate_monthly_kpi(
    db: Session,
    user_id: int,
    start_date: datetime,
    end_date: datetime,
    kpi_rule: KPIRule,
    company_maxima: CompanyMaxima
)
```

**Sync Components:**
- **Jira Sync:** Fetch issues via JQL, map users, calculate complexity
- **GitLab Sync:** Fetch commits, link to issues, MR tracking
- **Time Tracking:** Sync worklogs and time estimates
- **KPI Calculation:** Daily metrics and yearly aggregation

**Features:**
- Incremental sync with date range filtering
- Retry logic for API failures
- User mapping by Jira account ID and GitLab username
- Batch processing for performance

### 4.4 Feature Analyzer Service (`feature_analyzer.py`)

**Purpose:** AI-powered feature complexity scoring using LLM

**Key Classes:**

#### LLMFeatureScorer
```python
class LLMFeatureScorer:
    def __init__(self, api_key: str, model: str = "openai/gpt-4o-mini")
    def score_feature(
        self,
        issue_key: str,
        summary: str,
        description: str,
        issue_type: str,
        status: str,
        assignee: str
    ) -> dict
    def set_config_matrix(self, config_matrix: dict)
```

**LLM Scoring Dimensions:**
1. **technical_complexity (0-4)** - Implementation difficulty
2. **business_impact (0-4)** - Business value
3. **system_scope (0-4)** - System integration scope
4. **delivery_risk (0-2)** - Risk level
5. **ownership_level (0-1)** - Responsibility level

#### FeatureScorer (Rules-based fallback)
```python
class FeatureScorer:
    def __init__(self, config_matrix: dict)
    def score_feature(
        self,
        summary: str,
        description: str,
        issue_type: str,
        status: str
    ) -> dict
```

**Rules-based Scoring:**
- Keyword analysis (feature, bug, task, story, epic)
- Complexity keywords (simple, moderate, complex, critical)
- Priority weighting
- Status-based adjustments

**Point Mapping Function:**
```python
def kpi_points_from_total(total_score: float, point_map: list) -> int
```

**Point Map Tiers:**
```python
point_map = [
    [18, 25],   # 18-20 points → 25 KPI points
    [15, 20],   # 15-17 points → 20 KPI points
    [12, 15],   # 12-14 points → 15 KPI points
    [9, 10],    # 9-11 points → 10 KPI points
    [6, 7],     # 6-8 points → 7 KPI points
    [3, 4],     # 3-5 points → 4 KPI points
    [0, 1]      # 0-2 points → 1 KPI point
]
```

### 4.5 Scheduler Service (`scheduler.py`)

**Purpose:** Background task scheduling with APScheduler

**Scheduled Jobs:**
```python
@scheduler.scheduled_job('interval', minutes=60)
def sync_sprints_job():
    """Sync Jira sprints every 60 minutes"""

@scheduler.scheduled_job('interval', minutes=60)
def calculate_kpi_job():
    """Calculate daily KPI metrics every 60 minutes"""

@scheduler.scheduled_job('cron', hour=2)
def full_system_sync():
    """Full system sync at 2 AM daily"""
```

**Job Management:**
- Start/stop scheduler
- Job status monitoring
- Manual job triggering
- Job history tracking

### 4.6 Webhook Service (`webhooks.py`)

**Purpose:** Handle incoming Jira and GitLab webhooks

**Endpoints:**
```python
@router.post("/jira")
async def jira_webhook(request: Request, background_tasks: BackgroundTasks, db: Session)

@router.post("/gitlab")
async def gitlab_webhook(request: Request, background_tasks: BackgroundTasks, db: Session)
```

**Current Implementation:**
- Basic webhook receiving
- User lookup by email
- Background task queuing for comprehensive sync
- Event logging

**Planned Enhancements (see Section 9):**
- Signature verification
- Event normalization
- Incremental processing
- Retry logic
- Queue management

### 4.7 Board Management Service (`multi_board_sync.py`)

**Purpose:** Multi-board Jira support per user

**Endpoints:**
- `GET /api/v1/users/{user_id}/boards` - Get user's Jira boards
- `POST /api/v1/users/{user_id}/boards` - Assign boards to user
- `DELETE /api/v1/users/{user_id}/boards/{board_id}` - Remove board assignment
- `GET /api/v1/boards` - List all available boards

**Functionality:**
- Store multiple Jira board IDs per user (JSON field)
- Track currently active board
- Sync across all assigned boards
- Board-specific issue filtering

### 4.8 Encryption Service (`encrypt.py`)

**Purpose:** Token and secret encryption for secure storage

**Key Functions:**
```python
def encrypt_token(token: str, key: str) -> str
def decrypt_token(encrypted_token: str, key: str) -> str
```

**Encryption Method:**
- Fernet symmetric encryption
- Base64 encoding for database storage
- Environment key management
- Masking for API responses

### 4.9 Database Service (`engine.py`)

**Purpose:** Database engine and session management

**Key Components:**
```python
# Database engine
engine = create_async_engine(DATABASE_URL, echo=False)

# Session factory
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Dependency injection
async def get_db() -> AsyncGenerator[AsyncSession, None]
```

**Connection Pooling:**
- Pool size: 20 connections
- Max overflow: 10 connections
- Pool timeout: 30 seconds
- Pool recycle: 3600 seconds

---

## 5. Application Workflow

### 5.1 User Authentication Flow

```
┌─────────────┐
│   User      │
│ (Login UI)  │
└──────┬──────┘
       │
       │ 1. POST /api/v1/auth/login
       │    {username, password}
       ▼
┌─────────────────────────────────────────────┐
│            Backend (FastAPI)                │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │  1. Call HRIS API                     │  │
│  │     POST https://hris-api.../login    │  │
│  │  ┌─────────────────────────────────┐  │  │
│  │  │  2. Receive HRIS token          │  │  │
│  │  │  3. Sync user profile           │  │  │
│  │  │  4. Sync subordinates            │  │  │
│  │  └─────────────────────────────────┘  │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  5. Store token in supervisor_token_store   │
│  6. Return token to frontend                 │
└─────────────────────────────────────────────┘
       │
       │ 2. Return token
       ▼
┌─────────────┐
│  Frontend   │
│  (React)    │
│             │
│  3. Store token in localStorage           │
│  4. Set Authorization header               │
└─────────────┘
       │
       │ 3. Request data with token
       │    GET /api/v1/kpi/yearly-performance
       │    Authorization: Bearer {token}
       ▼
┌─────────────────────────────────────────────┐
│            Backend (FastAPI)                │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │  1. Verify token from store          │  │
│  │  2. Get user ID from token           │  │
│  │  3. Fetch user data from DB          │  │
│  │  4. Calculate KPI metrics            │  │
│  │  5. Return results                   │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

### 5.2 Data Synchronization Flow

```
┌─────────────────────────────────────────────────────────┐
│                  Scheduler (APScheduler)               │
│  Every 60 minutes or manual trigger                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Trigger sync_user_comprehensive()
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Sync Service (comprehensive_sync.py)       │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Jira Sync    │ │ GitLab Sync  │ │ KPI Calc     │
└──────────────┘ └──────────────┘ └──────────────┘
        │            │            │
        ▼            ▼            ▼
┌─────────────────────────────────────────────────────────┐
│                    Database Operations                   │
│  1. Fetch user's Jira account ID / GitLab username     │
│  2. Query Jira API for user's issues (JQL)             │
│  3. Query GitLab API for user's commits                │
│  4. Upsert raw_jira_issues                             │
│  5. Upsert raw_gitlab_commits                          │
│  6. Calculate complexity scores (LLM or rules)         │
│  7. Update kpi_employee_daily                          │
│  8. Update user_yearly_metrics                         │
│  9. Update company_maxima                              │
└─────────────────────────────────────────────────────────┘
```

### 5.3 KPI Calculation Flow

```
┌─────────────────────────────────────────────────────────┐
│                  Data Collection Phase                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ 1. Fetch raw issues from database
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Feature Complexity Scoring                 │
│  (feature_analyzer.py - LLMFeatureScorer)              │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ LLM Scoring  │ │Rules Fallback│ │Cache Check   │
│ (OpenRouter) │ │ (Keywords)   │ │ (Redis)      │
└──────────────┘ └──────────────┘ └──────────────┘
        │            │            │
        └────────────┼────────────┘
                     │
                     │ 2. Calculate complexity_score
                     │    (0-20 points from 5 dimensions)
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  Daily Aggregation                      │
│  (kpi_employee_daily table)                             │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ 3. Aggregate by user, date, sprint
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  Yearly Aggregation                      │
│  (user_yearly_metrics table)                            │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ 4. Sum daily metrics by year
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  Company Maxima                         │
│  (company_maxima table)                                 │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ 5. Find max values per division/period
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  Final KPI Score                        │
│  Formula: (user_complexity_sp / max_complexity_sp) * 100│
└─────────────────────────────────────────────────────────┘
```

### 5.4 Dashboard Display Flow

```
┌─────────────┐
│  Frontend   │
│  (React)    │
└──────┬──────┘
       │
       │ 1. GET /api/v1/kpi/yearly-performance?year=2025
       ▼
┌─────────────────────────────────────────────┐
│            Backend (FastAPI)                │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │  1. Verify authentication token      │  │
│  │  2. Get user ID from token           │  │
│  │  3. Check cache (60-second TTL)      │  │
│  │  4. If cache miss:                   │  │
│  │     a. Fetch user_yearly_metrics     │  │
│  │     b. Fetch company_maxima          │  │
│  │     c. Calculate final percentages   │  │
│  │     d. Store in cache                │  │
│  │  5. Return cached data               │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
       │
       │ 2. Return JSON
       ▼
┌─────────────┐
│  Frontend   │
│  (React)    │
│             │
│  3. Parse JSON data                      │
│  4. Update charts and displays           │
│  5. Show user KPI, team KPI, company max │
└─────────────┘
```

---

## 6. KPI Calculation Mechanism

### 6.1 Overview

The KPI calculation uses a **relative scoring system** where user performance is compared against company maxima within the same period and division. This ensures fair comparison across different teams and projects.

### 6.2 Calculation Pipeline

#### Step 1: Data Collection
```python
# Fetch raw issues from database
raw_issues = db.query(RawJiraIssue).filter(
    RawJiraIssue.assignee == user_email,
    RawJiraIssue.created_date >= period_start,
    RawJiraIssue.created_date <= period_end
).all()
```

#### Step 2: Complexity Scoring
```python
# Score each issue using LLM or rules
for issue in raw_issues:
    if issue.complexity_score:
        score = issue.complexity_score  # Use cached score
    else:
        # Calculate new score
        result = llm_scorer.score_feature(
            issue_key=issue.issue_key,
            summary=issue.summary,
            description=issue.description,
            issue_type=issue.issue_type,
            status=issue.status,
            assignee=issue.assignee
        )
        score = result['total_score']
        
        # Store score
        issue.complexity_score = score
        issue.score_type = 'llm'
        issue.model_used = 'gpt-4o-mini'
        issue.complexity_detail = result['detail']
```

#### Step 3: Daily Aggregation
```python
# Aggregate metrics by day
daily_metrics = {}
for issue in raw_issues:
    date = issue.created_date.date()
    if date not in daily_metrics:
        daily_metrics[date] = {
            'daily_raw_sp': 0,
            'daily_complexity_sp': 0,
            'daily_issues_cnt': 0,
            'daily_c_sp': 0,
            'daily_i_sp': 0,
            'daily_s_sp': 0,
            'daily_r_sp': 0,
            'daily_o_sp': 0
        }
    
    daily_metrics[date]['daily_complexity_sp'] += issue.complexity_score
    daily_metrics[date]['daily_issues_cnt'] += 1
    
    # Component scores
    detail = issue.complexity_detail or {}
    daily_metrics[date]['daily_c_sp'] += detail.get('technical_complexity', 0)
    daily_metrics[date]['daily_i_sp'] += detail.get('business_impact', 0)
    daily_metrics[date]['daily_s_sp'] += detail.get('system_scope', 0)
    daily_metrics[date]['daily_r_sp'] += detail.get('delivery_risk', 0)
    daily_metrics[date]['daily_o_sp'] += detail.get('ownership_level', 0)
```

#### Step 4: Yearly Aggregation
```python
# Sum daily metrics for the year
yearly_metrics = {
    'total_complexity_sp': sum(d['daily_complexity_sp'] for d in daily_metrics.values()),
    'total_issues_cnt': sum(d['daily_issues_cnt'] for d in daily_metrics.values()),
    'total_c_sp': sum(d['daily_c_sp'] for d in daily_metrics.values()),
    'total_i_sp': sum(d['daily_i_sp'] for d in daily_metrics.values()),
    'total_s_sp': sum(d['daily_s_sp'] for d in daily_metrics.values()),
    'total_r_sp': sum(d['daily_r_sp'] for d in daily_metrics.values()),
    'total_o_sp': sum(d['daily_o_sp'] for d in daily_metrics.values())
}
```

#### Step 5: Company Maxima Calculation
```python
# Find max values across all users in the same period/division
company_maxima = db.query(CompanyMaxima).filter(
    CompanyMaxima.period_start == year_start,
    CompanyMaxima.period_end == year_end,
    CompanyMaxima.division_id == user_division_id
).first()

if not company_maxima:
    # Calculate new maxima
    all_users = db.query(UserYearlyMetrics).filter(
        UserYearlyMetrics.year == year,
        UserYearlyMetrics.division_id == user_division_id
    ).all()
    
    company_maxima = CompanyMaxima(
        period_start=year_start,
        period_end=year_end,
        division_id=user_division_id,
        max_complexity_sp=max(u.total_complexity_sp for u in all_users),
        max_issues_cnt=max(u.total_issues_cnt for u in all_users),
        max_c_sp=max(u.total_c_sp for u in all_users),
        max_i_sp=max(u.total_i_sp for u in all_users),
        max_s_sp=max(u.total_s_sp for u in all_users),
        max_r_sp=max(u.total_r_sp for u in all_users),
        max_o_sp=max(u.total_o_sp for u in all_users)
    )
    db.add(company_maxima)
```

#### Step 6: Final KPI Score
```python
# Calculate final percentage based on company maxima
if company_maxima.max_complexity_sp > 0:
    final_percentage = (yearly_metrics['total_complexity_sp'] / company_maxima.max_complexity_sp) * 100
else:
    final_percentage = 0

# Alternative: Component-based scoring
component_percentage = 0
components = ['c', 'i', 's', 'r', 'o']
for comp in components:
    user_score = yearly_metrics[f'total_{comp}_sp']
    max_score = getattr(company_maxima, f'max_{comp}_sp')
    if max_score > 0:
        component_percentage += (user_score / max_score) * 20  # Each component is 20% of total

component_percentage = min(component_percentage, 100)
```

### 6.3 Scoring Formula

#### Complexity-Based Score
```
Final KPI % = (User Complexity Score / Company Max Complexity Score) × 100

Where:
- User Complexity Score = Sum of all issue complexity scores (0-20 each)
- Company Max Complexity Score = Highest complexity score among all users
```

#### Component-Based Score
```
Final KPI % = Σ (User Component Score / Company Max Component Score) × 20

Components:
- Technical Complexity (20%)
- Business Impact (20%)
- System Scope (20%)
- Delivery Risk (20%)
- Ownership Level (20%)
```

### 6.4 Point Mapping

Total complexity scores (0-20) are mapped to KPI points:

```python
point_map = [
    [18, 25],   # 18-20 points → 25 KPI points
    [15, 20],   # 15-17 points → 20 KPI points
    [12, 15],   # 12-14 points → 15 KPI points
    [9, 10],    # 9-11 points → 10 KPI points
    [6, 7],     # 6-8 points → 7 KPI points
    [3, 4],     # 3-5 points → 4 KPI points
    [0, 1]      # 0-2 points → 1 KPI point
]
```

### 6.5 Configuration Matrix

The KPI calculation is controlled by a JSON configuration matrix:

```json
{
  "max_c": 4,
  "max_i": 4,
  "max_s": 4,
  "max_r": 2,
  "max_o": 1,
  "point_map": [
    [18, 25],
    [15, 20],
    [12, 15],
    [9, 10],
    [6, 7],
    [3, 4],
    [0, 1]
  ],
  "scoring_method": "llm",
  "fallback_method": "rules"
}
```

**Parameters:**
- `max_c`, `max_i`, `max_s`: Maximum scores for technical complexity, business impact, system scope (0-4)
- `max_r`: Maximum score for delivery risk (0-2)
- `max_o`: Maximum score for ownership level (0-1)
- `point_map`: Mapping from total score to KPI points
- `scoring_method`: Primary scoring method (llm or rules)
- `fallback_method`: Fallback method if primary fails

---

## 7. LLM Integration

### 7.1 LLM Service Overview

The KPI Dashboard integrates with **OpenRouter API** to use **GPT-4o-mini** for AI-powered feature complexity scoring. This provides more accurate and nuanced complexity assessments compared to traditional keyword-based scoring.

### 7.2 LLM Service Configuration

**Environment Variables:**
```bash
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL=openai/gpt-4o-mini
```

**Configuration:**
- **API Provider:** OpenRouter
- **Model:** OpenAI GPT-4o-mini
- **Endpoint:** `https://openrouter.ai/api/v1/chat/completions`
- **Timeout:** 30 seconds
- **Retry Attempts:** 3
- **Fallback:** Rules-based scoring

### 7.3 LLM Scoring Process

#### Step 1: Prompt Construction
```python
def construct_prompt(
    issue_key: str,
    summary: str,
    description: str,
    issue_type: str,
    status: str,
    config_matrix: dict
) -> str:
    prompt = f"""
    You are an expert technical complexity analyst. Rate the following Jira issue on a scale of 0-20 points total.

    **Issue Details:**
    - Key: {issue_key}
    - Summary: {summary}
    - Description: {description}
    - Type: {issue_type}
    - Status: {status}

    **Scoring Dimensions (Maximum Points):**
    1. Technical Complexity (0-{config_matrix['max_c']}): Implementation difficulty, technical challenges, code complexity
    2. Business Impact (0-{config_matrix['max_i']}): Business value, revenue impact, strategic importance
    3. System Scope (0-{config_matrix['max_s']}): Integration scope, affected systems, cross-team impact
    4. Delivery Risk (0-{config_matrix['max_r']}): Timeline risk, dependencies, uncertainty
    5. Ownership Level (0-{config_matrix['max_o']}): Team ownership, leadership involvement

    **Guidelines:**
    - Technical Complexity: Consider code changes, database changes, API changes, testing requirements
    - Business Impact: Consider user impact, revenue impact, strategic alignment
    - System Scope: Consider microservices affected, external integrations, data flow
    - Delivery Risk: Consider dependencies, team availability, technical unknowns
    - Ownership Level: Consider if it's a team project, individual project, or founder-led

    **Output Format (JSON):**
    {{
        "technical_complexity": <0-{config_matrix['max_c']}>,
        "business_impact": <0-{config_matrix['max_i']}>,
        "system_scope": <0-{config_matrix['max_s']}>,
        "delivery_risk": <0-{config_matrix['max_r']}>,
        "ownership_level": <0-{config_matrix['max_o']}>,
        "total_score": <sum of all dimensions>,
        "explanation": "<brief explanation of scoring>"
    }}
    """
    return prompt
```

#### Step 2: API Request
```python
async def call_llm_api(prompt: str, api_key: str, model: str) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://kpi-dashboard-xi-murex.vercel.app",
        "X-Title": "KPI Dashboard"
    }
    
    data = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are an expert technical complexity analyst. Always respond with valid JSON only."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.3,  # Low temperature for consistent scoring
        "max_tokens": 500
    }
    
    response = await httpx.AsyncClient().post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=data,
        timeout=30.0
    )
    
    if response.status_code == 200:
        result = response.json()
        content = result['choices'][0]['message']['content']
        return json.loads(content)
    else:
        raise Exception(f"LLM API error: {response.status_code} - {response.text}")
```

#### Step 3: Result Processing
```python
def process_llm_result(llm_result: dict, config_matrix: dict) -> dict:
    # Extract scores
    scores = {
        'technical_complexity': min(llm_result['technical_complexity'], config_matrix['max_c']),
        'business_impact': min(llm_result['business_impact'], config_matrix['max_i']),
        'system_scope': min(llm_result['system_scope'], config_matrix['max_s']),
        'delivery_risk': min(llm_result['delivery_risk'], config_matrix['max_r']),
        'ownership_level': min(llm_result['ownership_level'], config_matrix['max_o'])
    }
    
    # Calculate total
    total_score = sum(scores.values())
    
    # Map to KPI points
    kpi_points = kpi_points_from_total(total_score, config_matrix['point_map'])
    
    return {
        'scores': scores,
        'total_score': total_score,
        'kpi_points': kpi_points,
        'explanation': llm_result.get('explanation', ''),
        'score_type': 'llm',
        'model_used': 'gpt-4o-mini'
    }
```

### 7.4 Error Handling & Fallback

```python
async def score_feature_with_fallback(
    issue_key: str,
    summary: str,
    description: str,
    issue_type: str,
    status: str,
    config_matrix: dict,
    llm_scorer: LLMFeatureScorer,
    rules_scorer: FeatureScorer
) -> dict:
    try:
        # Try LLM scoring
        result = await llm_scorer.score_feature(
            issue_key=issue_key,
            summary=summary,
            description=description,
            issue_type=issue_type,
            status=status,
            assignee=""
        )
        logger.info(f"LLM scoring successful for {issue_key}")
        return result
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            logger.error(f"LLM scoring failed (401 Unauthorized) for {issue_key}, using rules fallback")
        else:
            logger.error(f"LLM scoring failed ({e.response.status_code}) for {issue_key}, using rules fallback")
        
    except Exception as e:
        logger.error(f"LLM scoring failed ({str(e)}) for {issue_key}, using rules fallback")
    
    # Fallback to rules-based scoring
    return rules_scorer.score_feature(
        summary=summary,
        description=description,
        issue_type=issue_type,
        status=status
    )
```

### 7.5 Caching Strategy

```python
# Check for cached score before calling LLM
def get_cached_score(db: Session, issue_key: str) -> dict:
    issue = db.query(RawJiraIssue).filter(
        RawJiraIssue.issue_key == issue_key
    ).first()
    
    if issue and issue.complexity_score is not None:
        return {
            'total_score': issue.complexity_score,
            'scores': issue.complexity_detail,
            'score_type': issue.score_type,
            'model_used': issue.model_used
        }
    
    return None
```

### 7.6 Performance Optimization

**Caching:**
- Complexity scores are cached in the database
- Reuse scores when recalculating KPI
- Cache TTL: 30 days (configurable)

**Batch Processing:**
- Process issues in batches of 50
- Parallel processing for large datasets
- Rate limiting to avoid API throttling

**Error Resilience:**
- Automatic fallback to rules-based scoring
- Retry logic with exponential backoff
- Logging of all LLM calls and failures

### 7.7 LLM Scoring Example

**Input:**
```json
{
  "issue_key": "FR-472872",
  "summary": "Implement real-time webhook integration for Jira and GitLab",
  "description": "Create webhook endpoints to receive real-time updates from Jira and GitLab. Implement signature verification, event normalization, and incremental KPI calculation.",
  "issue_type": "Feature",
  "status": "In Progress"
}
```

**LLM Output:**
```json
{
  "technical_complexity": 4,
  "business_impact": 3,
  "system_scope": 4,
  "delivery_risk": 2,
  "ownership_level": 1,
  "total_score": 14,
  "explanation": "High technical complexity due to security requirements and real-time processing. High system scope affecting multiple services. Moderate business impact for improved KPI accuracy. Medium delivery risk due to integration complexity. Team-owned project."
}
```

**Processed Result:**
```json
{
  "total_score": 14,
  "kpi_points": 15,
  "score_type": "llm",
  "model_used": "gpt-4o-mini",
  "scores": {
    "technical_complexity": 4,
    "business_impact": 3,
    "system_scope": 4,
    "delivery_risk": 2,
    "ownership_level": 1
  }
}
```

---

## 8. Multi-Team KPI Calculation

### 8.1 Overview

The KPI Dashboard supports **multi-team and multi-division KPI calculation** with the following features:

- Division-based isolation
- Team (group) level aggregation
- Cross-division comparison
- Company-wide maxima calculation
- Supervisor-subordinate hierarchy support

### 8.2 Organizational Structure

```
Company
│
├── Division: Technology
│   ├── Group: Frontend Team
│   │   ├── User: John Doe (Supervisor)
│   │   ├── User: Jane Smith
│   │   └── User: Bob Johnson
│   │
│   ├── Group: Backend Team
│   │   ├── User: Alice Brown (Supervisor)
│   │   └── User: Charlie Davis
│   │
│   └── Group: DevOps Team
│       └── User: David Wilson
│
├── Division: Marketing
│   └── Group: Marketing Team
│       ├── User: Emily Clark (Supervisor)
│       └── User: Frank Miller
│
└── Division: Finance
    └── Group: Finance Team
        └── User: Grace Lee
```

### 8.3 Division-Based Calculation

#### Isolation Strategy
```python
# Calculate company maxima per division
def calculate_division_maxima(db: Session, year: int, division_id: int):
    division_users = db.query(User).filter(
        User.division_id == division_id,
        User.is_active == True
    ).all()
    
    user_ids = [u.id for u in division_users]
    
    # Get yearly metrics for division users
    metrics = db.query(UserYearlyMetrics).filter(
        UserYearlyMetrics.user_id.in_(user_ids),
        UserYearlyMetrics.year == year
    ).all()
    
    # Calculate maxima
    company_maxima = CompanyMaxima(
        period_start=date(year, 1, 1),
        period_end=date(year, 12, 31),
        division_id=division_id,
        max_complexity_sp=max(m.total_complexity_sp for m in metrics) if metrics else 0,
        max_issues_cnt=max(m.total_issues_cnt for m in metrics) if metrics else 0,
        max_c_sp=max(m.total_c_sp for m in metrics) if metrics else 0,
        max_i_sp=max(m.total_i_sp for m in metrics) if metrics else 0,
        max_s_sp=max(m.total_s_sp for m in metrics) if metrics else 0,
        max_r_sp=max(m.total_r_sp for m in metrics) if metrics else 0,
        max_o_sp=max(m.total_o_sp for m in metrics) if metrics else 0,
        record_count=len(metrics)
    )
    
    return company_maxima
```

#### Division-Level KPI Calculation
```python
def calculate_division_kpi(db: Session, year: int, division_id: int):
    # Get company maxima for this division
    company_maxima = calculate_division_maxima(db, year, division_id)
    
    # Get all users in division
    users = db.query(User).filter(
        User.division_id == division_id,
        User.is_active == True
    ).all()
    
    # Calculate KPI for each user
    results = []
    for user in users:
        yearly_metrics = db.query(UserYearlyMetrics).filter(
            UserYearlyMetrics.user_id == user.id,
            UserYearlyMetrics.year == year
        ).first()
        
        if yearly_metrics and company_maxima.max_complexity_sp > 0:
            final_percentage = (yearly_metrics.total_complexity_sp / company_maxima.max_complexity_sp) * 100
            yearly_metrics.final_percentage = final_percentage
            
            results.append({
                'user_id': user.id,
                'full_name': user.full_name,
                'division': user.division.name,
                'group': user.group.name if user.group else None,
                'total_complexity_sp': yearly_metrics.total_complexity_sp,
                'final_percentage': final_percentage,
                'rank': None  # Will be calculated after sorting
            })
    
    # Sort by final_percentage
    results.sort(key=lambda x: x['final_percentage'], reverse=True)
    
    # Assign ranks
    for rank, result in enumerate(results, 1):
        result['rank'] = rank
    
    return results
```

### 8.4 Group (Team) Level Calculation

```python
def calculate_team_kpi(db: Session, year: int, group_id: int):
    # Get all users in group
    users = db.query(User).filter(
        User.group_id == group_id,
        User.is_active == True
    ).all()
    
    if not users:
        return []
    
    # Get division_id from first user
    division_id = users[0].division_id
    
    # Get company maxima for this division
    company_maxima = calculate_division_maxima(db, year, division_id)
    
    # Calculate team metrics
    team_results = []
    team_total_complexity_sp = 0
    team_total_issues_cnt = 0
    
    for user in users:
        yearly_metrics = db.query(UserYearlyMetrics).filter(
            UserYearlyMetrics.user_id == user.id,
            UserYearlyMetrics.year == year
        ).first()
        
        if yearly_metrics:
            user_result = {
                'user_id': user.id,
                'full_name': user.full_name,
                'position': user.position,
                'total_complexity_sp': yearly_metrics.total_complexity_sp,
                'total_issues_cnt': yearly_metrics.total_issues_cnt,
                'final_percentage': 0
            }
            
            if company_maxima.max_complexity_sp > 0:
                user_result['final_percentage'] = (yearly_metrics.total_complexity_sp / company_maxima.max_complexity_sp) * 100
            
            team_results.append(user_result)
            team_total_complexity_sp += yearly_metrics.total_complexity_sp
            team_total_issues_cnt += yearly_metrics.total_issues_cnt
    
    # Calculate team average
    team_avg_complexity_sp = team_total_complexity_sp / len(users) if users else 0
    team_avg_issues_cnt = team_total_issues_cnt / len(users) if users else 0
    
    # Team KPI (average of user percentages)
    team_final_percentage = sum(r['final_percentage'] for r in team_results) / len(team_results) if team_results else 0
    
    return {
        'team_id': group_id,
        'team_name': users[0].group.name if users and users[0].group else 'Unknown',
        'team_size': len(users),
        'team_avg_complexity_sp': team_avg_complexity_sp,
        'team_avg_issues_cnt': team_avg_issues_cnt,
        'team_final_percentage': team_final_percentage,
        'members': team_results
    }
```

### 8.5 Supervisor-Subordinate Hierarchy

```python
def get_subordinates(db: Session, user_id: int):
    """Get all direct and indirect subordinates of a user"""
    # Get direct subordinates
    direct = db.query(User).filter(User.supervisor_id == user_id).all()
    
    # Get indirect subordinates recursively
    all_subordinates = set(direct)
    queue = direct[:]
    
    while queue:
        current = queue.pop(0)
        subordinates = db.query(User).filter(User.supervisor_id == current.id).all()
        for sub in subordinates:
            if sub not in all_subordinates:
                all_subordinates.add(sub)
                queue.append(sub)
    
    return list(all_subordinates)

def calculate_supervisor_team_kpi(db: Session, year: int, supervisor_id: int):
    """Calculate KPI for supervisor's entire team (all subordinates)"""
    subordinates = get_subordinates(db, supervisor_id)
    
    if not subordinates:
        return []
    
    # Get division_id from supervisor
    supervisor = db.query(User).filter(User.id == supervisor_id).first()
    division_id = supervisor.division_id
    
    # Get company maxima for this division
    company_maxima = calculate_division_maxima(db, year, division_id)
    
    # Calculate KPI for all subordinates
    results = []
    for user in subordinates:
        yearly_metrics = db.query(UserYearlyMetrics).filter(
            UserYearlyMetrics.user_id == user.id,
            UserYearlyMetrics.year == year
        ).first()
        
        if yearly_metrics:
            result = {
                'user_id': user.id,
                'full_name': user.full_name,
                'position': user.position,
                'direct_subordinate': user.supervisor_id == supervisor_id,
                'total_complexity_sp': yearly_metrics.total_complexity_sp,
                'total_issues_cnt': yearly_metrics.total_issues_cnt,
                'final_percentage': 0
            }
            
            if company_maxima.max_complexity_sp > 0:
                result['final_percentage'] = (yearly_metrics.total_complexity_sp / company_maxima.max_complexity_sp) * 100
            
            results.append(result)
    
    # Sort by final_percentage
    results.sort(key=lambda x: x['final_percentage'], reverse=True)
    
    # Calculate team average
    team_avg = sum(r['final_percentage'] for r in results) / len(results) if results else 0
    
    return {
        'supervisor_id': supervisor_id,
        'supervisor_name': supervisor.full_name,
        'team_size': len(results),
        'team_avg_percentage': team_avg,
        'members': results
    }
```

### 8.6 Cross-Division Comparison

```python
def compare_divisions(db: Session, year: int):
    """Compare KPI performance across all divisions"""
    divisions = db.query(Division).all()
    
    comparison = []
    for division in divisions:
        # Calculate division KPI
        division_results = calculate_division_kpi(db, year, division.id)
        
        if division_results:
            division_avg = sum(r['final_percentage'] for r in division_results) / len(division_results)
            division_max = max(r['final_percentage'] for r in division_results)
            division_min = min(r['final_percentage'] for r in division_results)
            
            comparison.append({
                'division_id': division.id,
                'division_name': division.name,
                'team_size': len(division_results),
                'avg_percentage': division_avg,
                'max_percentage': division_max,
                'min_percentage': division_min,
                'top_performer': division_results[0]['full_name'] if division_results else None
            })
    
    # Sort by avg_percentage
    comparison.sort(key=lambda x: x['avg_percentage'], reverse=True)
    
    return comparison
```

### 8.7 API Endpoints for Multi-Team KPI

```python
@router.get("/kpi/yearly-performance")
async def get_yearly_performance(
    year: int = Query(None, description="Year (default: current year)"),
    division_id: int = Query(None, description="Filter by division"),
    group_id: int = Query(None, description="Filter by group/team"),
    include_subordinates: bool = Query(False, description="Include subordinates if supervisor"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get yearly KPI performance with multi-team support"""
    
    if not year:
        year = datetime.now().year
    
    # Supervisor view: show team
    if include_subordinates:
        result = calculate_supervisor_team_kpi(db, year, current_user.id)
        return result
    
    # Group view: show team
    elif group_id:
        result = calculate_team_kpi(db, year, group_id)
        return result
    
    # Division view: show division
    elif division_id:
        result = calculate_division_kpi(db, year, division_id)
        return result
    
    # Default: show individual user
    else:
        yearly_metrics = db.query(UserYearlyMetrics).filter(
            UserYearlyMetrics.user_id == current_user.id,
            UserYearlyMetrics.year == year
        ).first()
        
        if not yearly_metrics:
            return {"error": "No metrics found for this year"}
        
        return {
            'user_id': current_user.id,
            'full_name': current_user.full_name,
            'year': year,
            'total_complexity_sp': yearly_metrics.total_complexity_sp,
            'total_issues_cnt': yearly_metrics.total_issues_cnt,
            'final_percentage': yearly_metrics.final_percentage
        }

@router.get("/kpi/division-comparison")
async def get_division_comparison(
    year: int = Query(None, description="Year (default: current year)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Compare KPI performance across divisions"""
    if not year:
        year = datetime.now().year
    
    comparison = compare_divisions(db, year)
    return comparison
```

### 8.8 Multi-Team Calculation Flow

```
┌─────────────────────────────────────────────────────────┐
│              Multi-Team KPI Calculation                  │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Individual   │ │ Team/Group   │ │ Division     │
│ KPI          │ │ KPI          │ │ KPI          │
└──────────────┘ └──────────────┘ └──────────────┘
        │            │            │
        │            │            │
        ▼            ▼            ▼
┌─────────────────────────────────────────────────────────┐
│              Company Maxima (per division)               │
│  - max_complexity_sp                                    │
│  - max_issues_cnt                                       │
│  - max_c_sp, max_i_sp, max_s_sp, max_r_sp, max_o_sp    │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Compare against maxima
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Final KPI Percentage                       │
│  Formula: (user_score / division_max) × 100            │
└─────────────────────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Dashboard    │ │ Team Report  │ │ Division     │
│ Display      │ │ Display      │ │ Comparison   │
└──────────────┘ └──────────────┘ └──────────────┘
```

---

## 9. Jira Task Requirements

### 9.1 Webhook Integration Tasks

The following tasks have been defined for implementing webhook integration with Jira and GitLab:

#### Task 1: Database Schema Migration (PostgreSQL)
- **Ticket Type:** Technical Task
- **Priority:** P0 - Critical Path
- **Story Points:** 5

**Description:** Create PostgreSQL-compatible database migration to support webhook configuration, encrypted secrets storage, and IP whitelist functionality.

**Requirements:**
- Create `WebhookConfiguration` table
- Create `WebhookSecret` table
- Update `IntegrationSetting` table
- Create `WebhookIPWhitelist` table
- Migration must be idempotent

---

#### Task 2: Encrypted Webhook Secret Storage
- **Ticket Type:** Development Task
- **Priority:** P0 - Critical Path
- **Story Points:** 3

**Description:** Implement encrypted storage for webhook secrets using existing encryption infrastructure.

**Requirements:**
- Create `encrypt_webhook_secret()` function
- Create `decrypt_webhook_secret()` function
- Mask secrets in API responses
- Add secret rotation support

**API Endpoints:**
- `POST /api/v1/webhooks/secrets`
- `GET /api/v1/webhooks/secrets`
- `PUT /api/v1/webhooks/secrets/{id}`
- `DELETE /api/v1/webhooks/secrets/{id}`

---

#### Task 3: Jira Webhook Signature Verification
- **Ticket Type:** Development Task
- **Priority:** P0 - Critical Path
- **Story Points:** 4

**Description:** Implement HMAC signature verification for Jira webhooks using `X-Jira-Signature` header.

**Requirements:**
- Extract `X-Jira-Signature` header
- Compute HMAC SHA256 hash of payload
- Compare with received signature
- Reject invalid signatures (401)
- Use constant-time comparison

---

#### Task 4: GitLab Webhook Signature Verification
- **Ticket Type:** Development Task
- **Priority:** P0 - Critical Path
- **Story Points:** 3

**Description:** Implement webhook signature verification for GitLab using `X-Gitlab-Token` header.

**Requirements:**
- Extract `X-Gitlab-Token` header
- Compare token with stored secret
- Reject invalid tokens (401)
- Use constant-time comparison

---

#### Task 5: Event Normalization - Jira
- **Ticket Type:** Development Task
- **Priority:** P1 - High Priority
- **Story Points:** 4

**Description:** Create event normalization function to transform Jira webhook payloads into standard internal format.

**Requirements:**
- Extract user_id, issue_key, action_type, timestamp
- Extract relevant fields (assignee, reporter, status, etc.)
- Handle `issue_created` and `issue_updated` events
- Error handling for malformed payloads

---

#### Task 6: Event Normalization - GitLab
- **Ticket Type:** Development Task
- **Priority:** P1 - High Priority
- **Story Points:** 4

**Description:** Create event normalization function to transform GitLab webhook payloads into standard internal format.

**Requirements:**
- Extract user_id, project_id, mr_id, action_type, timestamp
- Extract commits array
- Handle `Push Hook` and `Merge Request Hook` events
- Error handling for malformed payloads

---

#### Task 7: Incremental Jira Sync
- **Ticket Type:** Development Task
- **Priority:** P0 - Critical Path
- **Story Points:** 8

**Description:** Implement incremental Jira synchronization that processes webhook payloads directly for real-time KPI updates.

**Requirements:**
- Upsert `raw_jira_issues` with webhook data
- Calculate complexity score using `LLMFeatureScorer`
- Update `kpi_employee_daily` metrics
- Trigger partial precompute for affected user
- Handle `issue_created` and `issue_updated` events
- Idempotent processing (duplicate handling)

---

#### Task 8: Incremental GitLab Sync
- **Ticket Type:** Development Task
- **Priority:** P0 - Critical Path
- **Story Points:** 8

**Description:** Implement incremental GitLab synchronization that processes webhook payloads for commits and merge requests.

**Requirements:**
- Process commits for push events
- Process MRs for merge request events
- Calculate feature complexity from MR descriptions
- Update KPI metrics based on commit/MR data
- Link commits to Jira issues

---

#### Task 9: Webhook Deduplication
- **Ticket Type:** Development Task
- **Priority:** P1 - High Priority
- **Story Points:** 4

**Description:** Implement webhook deduplication logic to prevent duplicate processing of the same event.

**Requirements:**
- Create `raw_jira_issue_events` and `raw_gitlab_events` tables
- Deduplication using event_id + timestamp
- Store webhook payloads for auditing
- Check for existing events before processing

---

#### Task 10: Webhook Retry Logic
- **Ticket Type:** Development Task
- **Priority:** P0 - Critical Path
- **Story Points:** 6

**Description:** Implement configurable retry logic for failed webhook processing with exponential backoff.

**Requirements:**
- Configurable max_retries (default: 3)
- Configurable backoff_base (default: 1.5)
- Configurable backoff_max (default: 60)
- Exponential backoff calculation
- Permanent failure logging

---

#### Task 11: Webhook Queue Management
- **Ticket Type:** Development Task
- **Priority:** P1 - High Priority
- **Story Points:** 6

**Description:** Implement background queue management for webhook retry processing using Celery/RQ with Redis.

**Requirements:**
- Set up Redis for job queue storage
- Create Celery tasks for webhook retry
- Queue depth monitoring
- Worker processes for queue consumption
- Queue priority handling

---

#### Task 12: Updated Webhook Endpoints
- **Ticket Type:** Development Task
- **Priority:** P0 - Critical Path
- **Story Points:** 8

**Description:** Update existing webhook endpoints to implement full webhook processing pipeline.

**Requirements:**
- Jira endpoint: signature verification, normalization, deduplication, incremental processing, retry logic
- GitLab endpoint: signature verification, normalization, deduplication, incremental processing, retry logic
- Store raw events for auditing
- Return appropriate HTTP status codes

**Webhook URLs:**
- Jira: `https://services-kpi-production.up.railway.app/api/v1/webhooks/jira`
- GitLab: `https://services-kpi-production.up.railway.app/api/v1/webhooks/gitlab`

---

#### Task 13: Credential Management API
- **Ticket Type:** Development Task
- **Priority:** P1 - High Priority
- **Story Points:** 5

**Description:** Create unified credential management API for storing and managing Jira API tokens and GitLab personal access tokens.

**Requirements:**
- Masked credential display
- Encrypted storage
- Token status validation
- CRUD operations for credentials

**API Endpoints:**
- `GET /api/v1/integrations/credentials`
- `POST /api/v1/integrations/credentials`
- `DELETE /api/v1/integrations/credentials/{service}`

---

#### Task 14: Webhook Configuration Management
- **Ticket Type:** Development Task
- **Priority:** P1 - High Priority
- **Story Points:** 5

**Description:** Create API endpoints for managing webhook configuration per division.

**Requirements:**
- Per-division webhook configuration
- Enable/disable webhooks
- Configure enabled events
- Set retry parameters
- Test webhook connectivity

**API Endpoints:**
- `GET /api/v1/webhooks/config`
- `POST /api/v1/webhooks/config`
- `POST /api/v1/webhooks/test`

---

#### Task 15: Webhook Monitoring & Status
- **Ticket Type:** Development Task
- **Priority:** P2 - Medium Priority
- **Story Points:** 4

**Description:** Create webhook monitoring endpoint to track webhook health, delivery status, and queue depth.

**Requirements:**
- Recent webhook deliveries
- Queue depth (pending, processing, failed)
- Success/failure rates
- Last delivery timestamp
- Average processing time

**API Endpoints:**
- `GET /api/v1/webhooks/status`
- `GET /api/v1/webhooks/logs`

---

#### Task 16: Rate Limiting & Security
- **Ticket Type:** Development Task
- **Priority:** P2 - Medium Priority
- **Story Points:** 4

**Description:** Implement rate limiting and enhanced security features for webhook endpoints.

**Requirements:**
- Rate limiting per IP and per webhook
- IP whitelist validation
- Request size limits
- Timeout settings
- Abuse detection and alerting

---

#### Task 17: Auto-Pause Full Sync During Webhook Burst
- **Ticket Type:** Development Task
- **Priority:** P2 - Medium Priority
- **Story Points:** 3

**Description:** Implement auto-pause of full comprehensive sync during high webhook activity.

**Requirements:**
- Monitor webhook queue depth
- Pause full sync when threshold exceeded
- Resume sync when queue clears
- Configurable thresholds

---

#### Task 18: Production Deployment
- **Ticket Type:** Deployment Task
- **Priority:** P0 - Critical Path
- **Story Points:** 8

**Description:** Deploy webhook integration to Railway production environment.

**Requirements:**
- Run PostgreSQL migration
- Set up Redis service
- Deploy Celery workers
- Configure environment variables
- Configure Jira webhooks
- Configure GitLab webhooks
- Monitor initial deliveries

**Environment Variables:**
- `REDIS_URL`
- `REDIS_CACHE_TTL`
- `WEBHOOK_RETRY_MAX`
- `WEBHOOK_BACKOFF_BASE`
- `WEBHOOK_BACKOFF_MAX`

---

#### Task 19: Testing & Validation
- **Ticket Type:** Testing Task
- **Priority:** P1 - High Priority
- **Story Points:** 6

**Description:** Comprehensive testing of webhook integration functionality.

**Requirements:**
- Unit tests for all functions
- Integration tests for end-to-end processing
- Performance tests
- Security tests (signature verification, IP whitelist, rate limiting)
- Manual testing scenarios

---

#### Task 20: Documentation
- **Ticket Type:** Documentation Task
- **Priority:** P1 - High Priority
- **Story Points:** 4

**Description:** Create comprehensive documentation for webhook integration.

**Requirements:**
- Setup guide for Jira and GitLab webhooks
- API documentation
- Troubleshooting guide
- Best practices
- Code examples

---

### 9.2 Task Summary

**Total Tasks:** 20  
**Total Story Points:** 101  
**Estimated Timeline:** 4-6 weeks (with 1-2 developers)

#### Critical Path (Must Complete First):
1. Task 1: Database Schema Migration
2. Task 2: Encrypted Webhook Secret Storage
3. Task 3: Jira Webhook Signature Verification
4. Task 4: GitLab Webhook Signature Verification
5. Task 5: Event Normalization - Jira
6. Task 6: Event Normalization - GitLab
7. Task 7: Incremental Jira Sync
8. Task 8: Incremental GitLab Sync
9. Task 10: Webhook Retry Logic
10. Task 12: Updated Webhook Endpoints
11. Task 13: Credential Management API
12. Task 18: Production Deployment

#### Priority Breakdown:
- **P0 (Critical):** 10 tasks, 51 story points
- **P1 (High):** 7 tasks, 37 story points
- **P2 (Medium):** 3 tasks, 13 story points

---

### 9.3 Required Information

**For Production Deployment:**
- ✅ Jira Access Token: `your_jira_token_here`
- ⏳ GitLab Personal Access Token: `[To be provided]`
- ⏳ Jira Webhook Secret (optional): `[To be provided]`
- ⏳ GitLab Webhook Secret (optional): `[To be provided]`

**For Jira Configuration:**
- ⏳ Jira Instance URL: `[To be provided]`
- ✅ Jira Project Keys: `FR`, `IRIS`, etc.

**For GitLab Configuration:**
- ⏳ GitLab Instance URL: `[To be provided]`
- ⏳ GitLab Project IDs: `[To be provided]`

---

### 9.4 Success Criteria

- [ ] Real-time KPI calculation when issues/commits are created
- [ ] Zero polling delays for KPI updates
- [ ] Reliable webhook delivery with retry logic
- [ ] Secure webhook verification with HMAC signatures
- [ ] Comprehensive monitoring and alerting
- [ ] Production deployment on Railway PostgreSQL
- [ ] Full documentation and troubleshooting guide

---

## 10. Technical Specifications

### 10.1 API Endpoints

#### Authentication
- `POST /api/v1/auth/login` - User login via HRIS
- `GET /api/v1/auth/verify` - Verify token
- `GET /api/v1/auth/me` - Get current user

#### KPI Endpoints
- `GET /api/v1/kpi/yearly-performance` - Yearly KPI performance
- `GET /api/v1/kpi/division-comparison` - Division comparison
- `GET /api/v1/kpi/team-performance` - Team KPI performance
- `POST /api/v1/kpi/rescore` - Trigger KPI rescoring

#### Sync Endpoints
- `POST /api/v1/sync/trigger` - Trigger manual sync
- `GET /api/v1/sync/status` - Get sync status
- `GET /api/v1/jobs/{job_id}` - Get job details

#### User Management
- `GET /api/v1/users` - List users
- `GET /api/v1/users/{user_id}` - Get user details
- `GET /api/v1/users/{user_id}/subordinates` - Get user's subordinates

#### Board Management
- `GET /api/v1/boards` - List all boards
- `GET /api/v1/users/{user_id}/boards` - Get user's boards
- `POST /api/v1/users/{user_id}/boards` - Assign boards to user
- `DELETE /api/v1/users/{user_id}/boards/{board_id}` - Remove board assignment

#### Webhook Endpoints
- `POST /api/v1/webhooks/jira` - Jira webhook
- `POST /api/v1/webhooks/gitlab` - GitLab webhook
- `GET /api/v1/webhooks/status` - Webhook status (planned)
- `GET /api/v1/webhooks/config` - Webhook configuration (planned)
- `POST /api/v1/webhooks/test` - Test webhook (planned)

#### Configuration Endpoints
- `GET /api/v1/integrations/credentials` - Get credentials (planned)
- `POST /api/v1/integrations/credentials` - Update credentials (planned)
- `GET /api/v1/kpi/rules` - Get KPI rules
- `POST /api/v1/kpi/rules` - Create KPI rule

### 10.2 Database Connection Settings

**Connection String Format:**
```python
DATABASE_URL = "postgresql://user:password@host:port/database"
```

**Connection Pool:**
- Pool size: 20
- Max overflow: 10
- Pool timeout: 30 seconds
- Pool recycle: 3600 seconds

### 10.3 Cache Configuration

**Cache Backend:** In-memory (FastAPICache)

**Cache TTL:** 60 seconds

**Cache Keys:**
- `kpi:yearly:{year}:{user_id}`
- `kpi:division:{division_id}:{year}`
- `kpi:team:{group_id}:{year}`

### 10.4 Rate Limiting

**Default Limits:**
- Per IP: 100 requests per minute
- Per endpoint: 200 requests per minute
- Webhook endpoints: 1000 requests per minute

**Headers:**
- `X-RateLimit-Limit`: Max requests per window
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset timestamp

### 10.5 Security Settings

**Encryption:**
- Algorithm: Fernet (symmetric encryption)
- Key: Environment variable `ENCRYPTION_KEY`
- Encoding: Base64

**Authentication:**
- Method: Bearer token
- Token source: HRIS API
- Token validation: In-memory store
- Token expiration: Based on HRIS settings

**CORS:**
- Allowed origins: Vercel frontend, Railway backend, local development
- Allowed methods: GET, POST, PUT, DELETE
- Allowed headers: Authorization, Content-Type

---

## 11. Deployment Architecture

### 11.1 Production Environment

**Platform:** Railway.app

**Services:**
1. **FastAPI Backend**
   - Language: Python 3.11
   - Framework: FastAPI
   - Database: PostgreSQL
   - Cache: In-memory
   - Task Scheduler: APScheduler
   - Deployment: Railway

2. **PostgreSQL Database**
   - Version: PostgreSQL 15
   - Provider: Railway
   - Location: `altaria.proxy.rlwy.net:54779`
   - Max connections: 50

3. **Redis (Planned)**
   - Purpose: Webhook queue management
   - Deployment: Railway
   - Persistence: AOF (Append Only File)

4. **Celery Workers (Planned)**
   - Purpose: Webhook retry processing
   - Concurrency: 4 workers
   - Deployment: Railway

**Frontend:**
- Platform: Vercel
- URL: https://kpi-dashboard-xi-murex.vercel.app
- Framework: React 19 + Vite

### 11.2 Environment Variables

**Backend (.env):**
```bash
# Database
DATABASE_URL=postgresql://user:password@host:port/database

# Encryption
ENCRYPTION_KEY=4mJaDitz09NUP49heumLSXKn0UcuTtNO0g3s5rFzbV0=

# LLM Configuration
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL=openai/gpt-4o-mini

# Sync Configuration
SYNC_SPRINTS_INTERVAL_MINUTES=60
SYNC_KPI_CALCULATION_INTERVAL_MINUTES=60

# Redis (Planned)
REDIS_URL=redis://host:port/0
REDIS_CACHE_TTL=3600

# Webhook Configuration (Planned)
WEBHOOK_RETRY_MAX=3
WEBHOOK_BACKOFF_BASE=1.5
WEBHOOK_BACKOFF_MAX=60
```

**Frontend (.env):**
```bash
VITE_API_URL=https://services-kpi-production.up.railway.app
VITE_APP_URL=https://kpi-dashboard-xi-murex.vercel.app
```

### 11.3 Deployment Process

**Backend Deployment:**
1. Push changes to GitHub
2. Railway automatically detects changes
3. Build process:
   - Install dependencies (requirements.txt)
   - Run database migrations
   - Start application with uvicorn
4. Health checks pass → deployment successful

**Frontend Deployment:**
1. Push changes to GitHub
2. Vercel automatically detects changes
3. Build process:
   - Install dependencies (npm install)
   - Build application (npm run build)
   - Deploy to edge network
4. Custom domain configuration (if needed)

### 11.4 Monitoring & Logging

**Application Logs:**
- Log level: INFO
- Log format: JSON
- Log retention: 30 days
- Log aggregation: Railway logs

**Health Checks:**
- Database health: `/api/v1/db/diagnostics`
- Application health: `/health`
- LLM API health: Internal monitoring

**Error Tracking:**
- HTTP errors: Logged with stack traces
- Database errors: Logged with query details
- LLM errors: Logged with prompt/response
- Webhook errors: Logged with payload

### 11.5 Backup Strategy

**Database Backups:**
- Automatic: Daily backups (Railway)
- Retention: 7 days
- Point-in-time recovery: 7 days
- Manual backup: Available via Railway CLI

**Configuration Backups:**
- Environment variables: Railway dashboard
- Integration tokens: Encrypted in database
- Webhook secrets: Encrypted in database

---

## 12. Security Considerations

### 12.1 Data Security

**Encryption:**
- Tokens and secrets encrypted using Fernet
- Encryption key stored in environment variables
- Webhook secrets encrypted separately
- Masking for API responses

**Access Control:**
- Role-based access control (RBAC)
- User access to own data only
- Supervisor access to subordinates' data
- Admin access to all data

**Data Privacy:**
- No PII in logs
- Token masking in responses
- Encrypted credentials
- Secure API key management

### 12.2 API Security

**Authentication:**
- Bearer token authentication
- Token validation on every request
- Session management via HRIS API
- Token expiration handling

**Authorization:**
- Role-based permissions
- Supervisor-subordinate hierarchy
- Division-based data isolation
- Admin-only endpoints

**Rate Limiting:**
- Per-IP rate limiting
- Per-endpoint rate limiting
- Burst protection
- Rate limit headers

**CORS:**
- Allowed origins whitelist
- Allowed methods whitelist
- Allowed headers whitelist
- Pre-flight request handling

### 12.3 Webhook Security

**Signature Verification:**
- HMAC SHA256 for Jira webhooks
- Token-based verification for GitLab
- Constant-time comparison
- Signature rejection (401)

**IP Whitelist:**
- Source IP validation
- CIDR notation support
- Admin override for testing
- IP logging for audit trail

**Payload Validation:**
- JSON schema validation
- Size limits (10MB)
- Content-Type validation
- Malformed payload rejection

### 12.4 Third-Party Integration Security

**Jira API:**
- API token storage (encrypted)
- Secure HTTPS connections
- Token rotation support
- Error handling without token exposure

**GitLab API:**
- Personal access token storage (encrypted)
- Secure HTTPS connections
- Scope-limited tokens
- Token rotation support

**OpenRouter API:**
- API key storage (encrypted)
- Secure HTTPS connections
- Rate limiting (OpenRouter side)
- Fallback to rules-based scoring

**HRIS API:**
- Token storage (in-memory only)
- Secure HTTPS connections
- No password storage
- Token expiration handling

### 12.5 Infrastructure Security

**Railway Security:**
- Private network isolation
- Environment variable encryption
- Automatic security updates
- DDoS protection

**Vercel Security:**
- HTTPS-only connections
- DDoS protection
- Automatic HTTPS certificates
- Edge security

**Database Security:**
- SSL/TLS encryption
- Connection encryption
- Row-level security (planned)
- Regular security updates

---

## Appendix A: Glossary

- **API:** Application Programming Interface
- **AST:** Abstract Syntax Tree
- **Backoff:** Delay between retry attempts
- **CI/CD:** Continuous Integration/Continuous Deployment
- **CORS:** Cross-Origin Resource Sharing
- **CRUD:** Create, Read, Update, Delete
- **HMAC:** Hash-based Message Authentication Code
- **HRIS:** Human Resource Information System
- **JSON:** JavaScript Object Notation
- **JQL:** Jira Query Language
- **KPI:** Key Performance Indicator
- **LLM:** Large Language Model
- **MR:** Merge Request
- **ORM:** Object-Relational Mapping
- **PAT:** Personal Access Token
- **RBAC:** Role-Based Access Control
- **SP:** Story Points
- **SSL/TLS:** Secure Sockets Layer/Transport Layer Security
- **TTL:** Time To Live

---

## Appendix B: Configuration Reference

### B.1 KPI Rule Configuration Matrix

```json
{
  "max_c": 4,
  "max_i": 4,
  "max_s": 4,
  "max_r": 2,
  "max_o": 1,
  "point_map": [
    [18, 25],
    [15, 20],
    [12, 15],
    [9, 10],
    [6, 7],
    [3, 4],
    [0, 1]
  ],
  "scoring_method": "llm",
  "fallback_method": "rules"
}
```

### B.2 Webhook Retry Configuration

```json
{
  "max_retries": 3,
  "backoff_base": 1.5,
  "backoff_max": 60,
  "queue_enabled": true,
  "queue_threshold": 100
}
```

### B.3 Jira Status Mapping

```json
{
  "to-do": "backlog",
  "in-progress": "active",
  "in-review": "review",
  "done": "completed",
  "blocked": "blocked"
}
```

---

## Appendix C: Contact Information

**Development Team:**
- Backend Lead: [Contact]
- Frontend Lead: [Contact]
- DevOps Engineer: [Contact]
- Product Owner: [Contact]

**Support:**
- Email: [Support Email]
- Slack: [Slack Channel]
- Documentation: [Documentation URL]

---

**Document End**

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-08-18 | Development Team | Initial document creation |

---

**Next Steps:**

1. **Review and Approve:** Review this technical design document with stakeholders
2. **Resource Allocation:** Assign developers to Jira tasks
3. **Timeline Planning:** Schedule sprint planning for webhook integration
4. **Environment Setup:** Prepare development and testing environments
5. **Begin Implementation:** Start with Task 1 (Database Schema Migration)

**For Questions or Clarifications:**

Please contact the Development Team or refer to the project repository for more information.