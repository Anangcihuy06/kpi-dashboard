# Workflow KPI Dashboard — GitLab & Jira

## 1. Tujuan

Membangun KPI Dashboard yang menggabungkan data aktivitas karyawan dari **GitLab** dan **Jira** dalam suatu **range waktu tertentu**, tanpa bergantung pada satu project atau satu sprint.

Prinsip utama:

> Ambil seluruh aktivitas pada periode tertentu → normalisasi → mapping ke employee → mapping ke project/sprint/issue → hitung KPI → tampilkan dashboard.

---

## 2. Masalah yang Harus Diselesaikan

Seorang employee dapat:

- Mengerjakan beberapa project sekaligus.
- Berpindah antar sprint.
- Mengerjakan issue Jira yang berbeda.
- Melakukan aktivitas GitLab pada repository berbeda.
- Memiliki identitas berbeda antara HRIS, Jira, dan GitLab.
- Mengubah aktivitas/issue yang sudah pernah tersinkronisasi.

Karena itu, KPI tidak boleh dibangun dengan asumsi:

```text
1 Employee = 1 Project = 1 Sprint
```

Model yang benar:

```text
1 Employee
   ├── Project A
   │    ├── Sprint 10
   │    └── Sprint 11
   │
   ├── Project B
   │    └── Sprint 20
   │
   └── Project C
        ├── Sprint 5
        └── Sprint 6
```

---

# 3. High-Level Architecture

```text
                         ┌──────────────┐
                         │    GitLab    │
                         └──────┬───────┘
                                │
                                │ API
                                ▼
                        ┌───────────────┐
                        │ GitLab Worker │
                        └──────┬────────┘
                               │
                               │
                               ▼
┌──────────────┐        ┌───────────────┐
│     Jira     │───────►│ Data Ingestion│
└──────┬───────┘        └───────┬───────┘
       │                        │
       │ API                    │
       ▼                        ▼
┌──────────────┐        ┌────────────────┐
│  Jira Worker │        │ Raw Data Store │
└──────────────┘        └───────┬────────┘
                                │
                                ▼
                        ┌────────────────┐
                        │ Data Normalizer │
                        └───────┬────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │ Activity Storage │
                       └────────┬─────────┘
                                │
                 ┌──────────────┼──────────────┐
                 ▼              ▼              ▼
             Employee        Project        Sprint
                 │              │              │
                 └──────────────┼──────────────┘
                                ▼
                         ┌────────────┐
                         │ KPI Engine │
                         └─────┬──────┘
                               │
                               ▼
                        ┌─────────────┐
                        │ KPI Database│
                        └──────┬──────┘
                               │
                               ▼
                        ┌─────────────┐
                        │ Next.js Web │
                        │  Dashboard  │
                        └─────────────┘
```

---

# 4. Data Flow

## Step 1 — User Menentukan Range Waktu

Contoh:

```text
From : 2026-08-01 00:00:00
To   : 2026-08-14 23:59:59
```

Dashboard mengirim:

```http
GET /api/kpi?from=2026-08-01&to=2026-08-14
```

Backend tidak langsung mengambil data dari GitLab/Jira.

Backend mengambil data yang sudah tersinkronisasi dari database.

---

# 5. Step 2 — Data Ingestion

Data dari GitLab dan Jira diambil menggunakan worker.

```text
GitLab API
   │
   ├── Projects
   ├── Users
   ├── Commits
   ├── Merge Requests
   ├── Events
   └── Repository activity
```

```text
Jira API
   │
   ├── Projects
   ├── Users
   ├── Issues
   ├── Worklogs
   ├── Sprints
   ├── Comments
   └── Issue History
```

Worker menyimpan data terlebih dahulu ke database.

---

# 6. Step 3 — Initial Sync

Saat system pertama kali dijalankan:

```text
HRIS
  │
  ▼
Employee Master
  │
  ▼
Identity Mapping
```

Kemudian:

```text
GitLab
  │
  ├── Users
  ├── Projects
  ├── Commits
  ├── Merge Requests
  └── Events
```

dan:

```text
Jira
  │
  ├── Users
  ├── Projects
  ├── Issues
  ├── Sprints
  ├── Worklogs
  └── History
```

Historical range ditentukan oleh kebutuhan KPI.

Contoh:

```text
2025-01-01 → NOW
```

Tidak harus mengambil seluruh history jika KPI hanya membutuhkan data 12 bulan terakhir.

---

# 7. Step 4 — Incremental Sync

Setelah initial sync selesai, gunakan incremental synchronization.

Contoh:

```text
Last Sync
2026-08-14 10:00
       │
       ▼
Current Time
2026-08-14 10:15
```

Worker hanya mengambil:

```text
10:00 → 10:15
```

Bukan:

```text
2025-01-01 → 2026-08-14
```

---

# 8. Sync State

Simpan posisi terakhir synchronization.

Table:

```text
sync_state
-----------------------------
id
source
entity
last_cursor
last_sync_at
status
error_message
updated_at
```

Contoh:

```text
gitlab | commits         | 2026-08-14T10:00:00
gitlab | merge_requests  | 2026-08-14T10:00:00
jira   | issues          | 2026-08-14T10:00:00
jira   | worklogs        | 2026-08-14T10:00:00
```

---

# 9. Step 5 — Employee Identity Mapping

Ini merupakan bagian penting.

Contoh:

```text
HRIS
employee_id = EMP00123
email       = andi@company.com
name        = Andi Wijaya
```

GitLab:

```text
user_id = 123
username = andi.w
email = andi@company.com
```

Jira:

```text
account_id = 712020
email = andi@company.com
```

Semua harus dipetakan:

```text
                    EMP00123
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
        GitLab User          Jira User
        user_id=123        account_id=712020
```

## Recommended Table

```text
employee_identity
--------------------------------
id
employee_id
source
external_user_id
username
email
created_at
updated_at
```

Contoh:

```text
EMP00123 | gitlab | 123      | andi.w
EMP00123 | jira   | 712020   | andi.w
```

Jangan menggunakan `name` sebagai primary identity.

Prioritas mapping:

1. External user ID yang sudah terdaftar.
2. Corporate email.
3. Username.
4. Manual mapping oleh admin jika diperlukan.

---

# 10. Step 6 — Raw Data Layer

Simpan response/data asli dari source sebelum normalisasi.

Contoh:

```text
raw_gitlab_commits
raw_gitlab_merge_requests
raw_gitlab_events

raw_jira_issues
raw_jira_worklogs
raw_jira_sprints
raw_jira_issue_history
```

Tujuannya:

- Audit.
- Reprocessing.
- Debugging.
- Perubahan algoritma KPI.
- Menghindari kehilangan data source.

---

# 11. Step 7 — Data Normalization

Data dari GitLab dan Jira memiliki struktur berbeda.

Normalisasi menjadi model aktivitas bersama:

```text
activity
--------------------------------
id
employee_id
source
activity_type
project_id
sprint_id
issue_id
reference_id
activity_at
metadata
created_at
updated_at
```

Contoh GitLab Commit:

```json
{
  "employee_id": "EMP00123",
  "source": "gitlab",
  "activity_type": "commit",
  "project_id": "mobile-app",
  "activity_at": "2026-08-05T10:20:00",
  "reference_id": "abc123"
}
```

Contoh Jira Worklog:

```json
{
  "employee_id": "EMP00123",
  "source": "jira",
  "activity_type": "worklog",
  "project_id": "HRIS",
  "issue_id": "HRIS-456",
  "sprint_id": "SPRINT-20",
  "activity_at": "2026-08-07T09:00:00"
}
```

---

# 12. Step 8 — Project Mapping

Setiap aktivitas harus memiliki hubungan dengan project jika source menyediakan informasi tersebut.

```text
Employee
   │
   ▼
Activity
   │
   ▼
Project
```

Contoh:

```text
EMP00123
   │
   ├── GitLab Project: mobile-app
   ├── GitLab Project: backend-api
   └── Jira Project: HRIS
```

Project tidak boleh diasumsikan hanya satu per employee.

---

# 13. Step 9 — Sprint Mapping

Sprint adalah konteks historis aktivitas.

Contoh:

```text
Issue HRIS-123

2026-08-01 → Sprint 20
2026-08-08 → Sprint 21
```

Jika KPI tanggal 2026-08-03 dihitung, aktivitas harus masuk:

```text
Sprint 20
```

Jika KPI tanggal 2026-08-10 dihitung:

```text
Sprint 21
```

Karena itu, jangan hanya menyimpan:

```text
issue.current_sprint
```

Simpan juga history.

Contoh:

```text
issue_sprint_history
--------------------------------
issue_id
sprint_id
valid_from
valid_to
```

---

# 14. Step 10 — Issue History

Selain sprint, perubahan status dan assignee juga perlu dipertimbangkan.

Contoh:

```text
HRIS-123

08:00
Assignee = Andi

13:00
Assignee = Budi

16:00
Status = Done
```

Data history memungkinkan system mengetahui siapa yang melakukan pekerjaan pada periode tertentu.

Model:

```text
issue_history
--------------------------------
issue_id
field
old_value
new_value
changed_by
changed_at
```

---

# 15. Step 11 — Activity Timeline

Setelah normalization:

```text
Employee EMP00123

2026-08-01
  ├── Jira Issue Started
  └── GitLab Commit

2026-08-02
  ├── GitLab Commit
  ├── MR Created
  └── Jira Worklog

2026-08-03
  ├── MR Review
  └── Jira Issue Done
```

Semua aktivitas berada dalam satu timeline.

---

# 16. Step 12 — Filter berdasarkan Range

Contoh user memilih:

```text
2026-08-01
    ↓
2026-08-14
```

Query:

```sql
SELECT *
FROM activity
WHERE activity_at >= '2026-08-01 00:00:00'
  AND activity_at <  '2026-08-15 00:00:00';
```

Kemudian group:

```text
Employee
    ↓
Project
    ↓
Sprint
    ↓
Issue
    ↓
Activity
```

---

# 17. Step 13 — KPI Aggregation

Jangan menghitung KPI langsung dari raw data setiap request dashboard.

Buat aggregation layer.

Contoh:

```text
kpi_employee_daily
--------------------------------
date
employee_id
project_id
sprint_id

commit_count
mr_created
mr_merged
mr_reviewed
issue_created
issue_completed
story_points_completed
worklog_minutes
bug_count
```

---

# 18. KPI Calculation

Contoh KPI:

## Delivery

```text
Issue Completed
Story Points Completed
Sprint Completion
Cycle Time
```

## Engineering

```text
Commit Count
MR Created
MR Merged
MR Reviewed
```

## Quality

```text
Bug Count
Reopened Issue
Rework
Review Participation
```

## Effort

```text
Worklog Hours
Active Days
```

Jangan menggunakan satu metric seperti commit count sebagai representasi utama productivity.

---

# 19. KPI Aggregation Flow

```text
Raw GitLab
     │
     ▼
Normalized Activity
     │
     ├──────────────┐
     │              │
     ▼              ▼
GitLab KPI       Jira KPI
     │              │
     └──────┬───────┘
            ▼
       KPI Aggregator
            │
            ▼
    kpi_employee_daily
            │
            ▼
      KPI Dashboard
```

---

# 20. Dashboard Query

User memilih:

```text
Date:
2026-08-01 → 2026-08-14
```

Backend:

```http
GET /api/kpi/employees?from=2026-08-01&to=2026-08-14
```

Response:

```json
{
  "employee": "EMP00123",
  "period": {
    "from": "2026-08-01",
    "to": "2026-08-14"
  },
  "summary": {
    "projects": 3,
    "sprints": 4,
    "issues_completed": 18,
    "story_points": 42,
    "mr_merged": 9,
    "mr_reviewed": 14,
    "worklog_hours": 72
  }
}
```

---

# 21. Drill Down Dashboard

Dashboard employee:

```text
Andi Wijaya

KPI Score: 87.4

Projects       3
Sprints        4
Issues Done   18
Story Points  42
MR Merged      9
MR Reviewed   14
Worklog       72h
```

Klik employee:

```text
Andi
│
├── HRIS
│   └── Sprint 20
│       ├── 8 Issues
│       ├── 21 SP
│       ├── 4 MR
│       └── 32h
│
├── Payment
│   └── Sprint 12
│       ├── 6 Issues
│       ├── 13 SP
│       ├── 3 MR
│       └── 20h
│
└── Mobile
    └── Sprint 8
        ├── 4 Issues
        ├── 8 SP
        ├── 2 MR
        └── 20h
```

---

# 22. Recommended Database Structure

```text
employees
employee_identity

projects
sprints
issues

gitlab_users
gitlab_projects
gitlab_commits
gitlab_merge_requests
gitlab_events

jira_users
jira_projects
jira_issues
jira_sprints
jira_worklogs
jira_issue_history
jira_sprint_history

activities

kpi_employee_daily

sync_state
sync_logs
```

---

# 23. Recommended Relationships

```text
employees
    │
    └── employee_identity
             │
       ┌─────┴─────┐
       ▼           ▼
    GitLab        Jira
       │           │
       └─────┬─────┘
             ▼
          activity
             │
       ┌─────┼──────┐
       ▼     ▼      ▼
    project sprint issue
             │
             ▼
        KPI Aggregator
             │
             ▼
    kpi_employee_daily
```

---

# 24. Worker Architecture

Recommended worker:

```text
                    Scheduler
                       │
                       ▼
                ┌──────────────┐
                │ Job Producer │
                └──────┬───────┘
                       │
                 ┌─────┴─────┐
                 ▼           ▼
          GitLab Worker   Jira Worker
                 │           │
                 └─────┬─────┘
                       ▼
                 Raw Data Store
                       │
                       ▼
                 Normalization
                       │
                       ▼
                    Activity
                       │
                       ▼
                  KPI Worker
                       │
                       ▼
                KPI Aggregation
```

Untuk implementasi Go, worker dapat menggunakan:

```text
Go
PostgreSQL
Redis / Queue
Cron / Scheduler
```

Queue tidak wajib untuk MVP, tetapi sangat membantu ketika jumlah project/user mulai besar.

---

# 25. Idempotency

Worker harus aman jika job dijalankan ulang.

Jangan sampai:

```text
Sync #1
100 activities

Sync #2
100 activities

Database
200 activities
```

Gunakan unique key.

Contoh:

```text
GitLab commit:

UNIQUE(
    source,
    activity_type,
    reference_id
)
```

Untuk Jira:

```text
UNIQUE(
    source,
    activity_type,
    reference_id
)
```

---

# 26. Retry & Failure Handling

Jika GitLab API gagal:

```text
Worker
  │
  ▼
API Error
  │
  ├── Retry 1
  ├── Retry 2
  ├── Retry 3
  │
  ▼
Failed
  │
  ▼
sync_logs
```

Simpan:

```text
sync_logs
--------------------------------
source
entity
started_at
finished_at
status
records_processed
error_message
```

---

# 27. Rate Limit Handling

Worker harus:

- Menggunakan pagination.
- Menggunakan incremental sync.
- Menghindari duplicate request.
- Menggunakan retry dengan exponential backoff.
- Mengontrol concurrency.
- Menyimpan cursor/watermark.

Jangan melakukan:

```text
Dashboard request
   ↓
1000 API calls
```

---

# 28. Recommended Sync Schedule

Contoh:

```text
Every 5 minutes
├── GitLab Events
├── GitLab Merge Requests
└── Jira Issue Updates

Every 10 minutes
├── Jira Worklogs
└── Jira Issue History

Every 1 hour
├── Projects
├── Users
└── Sprints

Every night
└── Reconciliation / Full Incremental Scan
```

Frekuensi dapat disesuaikan dengan volume data dan kebutuhan dashboard.

---

# 29. Reconciliation Job

Selain incremental sync, lakukan reconciliation.

Contoh:

```text
Every Night

Jira
  ↓
Updated Issues Last 24h

GitLab
  ↓
Updated MRs Last 24h

Compare
  ↓
Fix missing/inconsistent data
```

Tujuannya mengantisipasi:

- API failure.
- Worker crash.
- Deleted data.
- Data berubah setelah initial sync.
- Pagination error.
- Mapping error.

---

# 30. End-to-End Workflow

```text
                    ┌─────────────┐
                    │ HRIS Master │
                    └──────┬──────┘
                           │
                           ▼
                    Employee Mapping
                           │
                           ▼
        ┌─────────────────────────────────┐
        │                                 │
        ▼                                 ▼
     GitLab                              Jira
        │                                 │
        ▼                                 ▼
   API Collector                     API Collector
        │                                 │
        ▼                                 ▼
   Raw GitLab                         Raw Jira
        │                                 │
        └──────────────┬──────────────────┘
                       ▼
                 Data Normalizer
                       │
                       ▼
                  Identity Mapping
                       │
                       ▼
                Activity Generator
                       │
                       ▼
             Project/Sprint/Issue Mapping
                       │
                       ▼
                Activity Timeline
                       │
                       ▼
                  KPI Calculator
                       │
                       ▼
               KPI Daily Aggregate
                       │
                       ▼
                  KPI Database
                       │
                       ▼
                 Dashboard API
                       │
                       ▼
                  Next.js UI
```

---

# 31. Golden Rule

Gunakan prinsip berikut:

```text
SOURCE DATA
    ↓
RAW DATA
    ↓
NORMALIZED DATA
    ↓
ACTIVITY
    ↓
EMPLOYEE
    ↓
PROJECT
    ↓
SPRINT
    ↓
ISSUE
    ↓
KPI
    ↓
DASHBOARD
```

Bukan:

```text
Employee
   ↓
Current Project
   ↓
Current Sprint
   ↓
Current KPI
```

Karena model kedua akan menghasilkan KPI historis yang tidak akurat ketika employee berpindah project/sprint.

---

# 32. MVP Implementation Order

Implementasikan secara bertahap:

## Phase 1 — Master Data

```text
[ ] Employee
[ ] GitLab User
[ ] Jira User
[ ] Employee Identity Mapping
[ ] Project
```

## Phase 2 — GitLab

```text
[ ] Projects
[ ] Users
[ ] Commits
[ ] Merge Requests
[ ] Events
```

## Phase 3 — Jira

```text
[ ] Projects
[ ] Users
[ ] Issues
[ ] Sprints
[ ] Worklogs
[ ] Issue History
[ ] Sprint History
```

## Phase 4 — Activity

```text
[ ] Activity Model
[ ] Activity Normalization
[ ] Employee Mapping
[ ] Project Mapping
[ ] Sprint Mapping
[ ] Issue Mapping
```

## Phase 5 — KPI

```text
[ ] Delivery KPI
[ ] Engineering KPI
[ ] Quality KPI
[ ] Effort KPI
[ ] Employee Daily Aggregate
```

## Phase 6 — Dashboard

```text
[ ] Date Range Filter
[ ] Employee Filter
[ ] Project Filter
[ ] Sprint Filter
[ ] Employee Summary
[ ] Project Drill Down
[ ] Sprint Drill Down
[ ] Activity Timeline
```

## Phase 7 — Reliability

```text
[ ] Incremental Sync
[ ] Sync State
[ ] Retry
[ ] Rate Limit Handling
[ ] Idempotency
[ ] Reconciliation
[ ] Monitoring
[ ] Audit Log
```

---

# 33. Recommended Final Stack

```text
Frontend
──────────────
Next.js
TypeScript
React
Chart Library

Backend
──────────────
Go
REST API
Worker

Database
──────────────
PostgreSQL

Queue
──────────────
Redis / Queue system

Scheduler
──────────────
Cron / Scheduler

External Sources
──────────────
GitLab API
Jira REST API

Optional
──────────────
Prometheus
Grafana
OpenTelemetry
```

---

# 34. Kesimpulan

Untuk kasus employee yang mengerjakan banyak project dan sprint, gunakan pendekatan:

```text
TIME RANGE
    ↓
COLLECT ALL ACTIVITIES
    ↓
NORMALIZE
    ↓
MAP EMPLOYEE
    ↓
MAP PROJECT
    ↓
MAP SPRINT
    ↓
MAP ISSUE
    ↓
CALCULATE KPI
    ↓
AGGREGATE
    ↓
DASHBOARD
```

Dengan pendekatan ini, query:

```text
2026-08-01 → 2026-08-14
```

akan menghasilkan seluruh pekerjaan employee pada periode tersebut, walaupun employee:

```text
Project A → Sprint 10
Project A → Sprint 11
Project B → Sprint 5
Project C → Sprint 20
```

dalam periode yang sama.

**Kunci desainnya adalah Activity + Identity Mapping + Historical State + Incremental Sync.**
