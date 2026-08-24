# Dokumentasi Sistem KPI Dashboard Dinamis & Multi-Divisi

---

## 1. Product Requirements Document (PRD)

### 1.1 Ringkasan Eksekutif
Sistem KPI Dashboard Dinamis adalah platform manajemen kinerja karyawan enterprise yang dirancang untuk mengukur, menganalisis, dan mengakumulasi performa individu maupun tim secara otomatis dan objektif. Platform ini terintegrasi secara langsung (*native*) dengan **Jira Software API** dan **GitLab API** untuk otomatisasi metrik teknis divisi IT, serta menyediakan **Engine Rule-Driven Dinamis** agar dapat diterapkan secara fleksibel pada seluruh divisi non-IT (Marketing, Finance, HR, Sales, Operasional) tanpa memerlukan perubahan kodingan (*zero code deployment for new rules*).

### 1.2 Masalah & Tujuan
* **Permasalahan Utama:**
  1. Penilaian KPI karyawan IT masih sering dilakukan secara manual dan subjektif.
  2. Ketersediaan data aktivitas teknis di Jira (Story Points, Bug Count, Velocity) dan GitLab (Merge Requests, Code Reviews, Commits) belum teragregasi secara otomatis ke dalam penilaian performa.
  3. Setiap divisi memiliki matriks, rumus, dan bobot penilaian yang berbeda serta sering mengalami perubahan (*dynamic requirements*).
  4. Sulitnya melacak akumulasi tren performa antar-sprint (siklus pendek) hingga periode tahunan/triwulan (siklus panjang).
* **Tujuan Utama:**
  1. Otomatisasi penarikan data dari Jira dan GitLab secara presisi dan terjadwal (*real-time / cron-based*).
  2. Menyediakan *Calculation Engine* berbasis Python yang aman (*safe evaluation*) untuk mengeksekusi ekspresi matematika bebas dari konfigurasi JSON/Database.
  3. Menyediakan antarmuka manajemen penilaian dinamis (*Dynamic Matrix Management*) bagi Admin/HR untuk mengatur bobot, indikator, dan formula per divisi.
  4. Menyediakan *Dashboard Analytics* berbasis Next.js dengan tampilan performa per-sprint dan akumulasi kumulatif.

### 1.3 Peran Pengguna (User Personas & Roles)
1. **Super Admin / HR Manager:**
   - Mengelola master data divisi, jabatan, dan pengguna.
   - Mengatur matriks KPI, menentukan rumus matematika, indikator, dan bobot per divisi.
   - Mengunci (*finalize*) nilai KPI sprint dan menjalankan kalkulasi akumulasi periode.
2. **Division Lead / Engineering Manager:**
   - Memantau performa anggota tim pada sprint aktif maupun historis.
   - Memverifikasi data narikan dari Jira/GitLab serta menginput nilai kuantitaf/kualitatif manual untuk divisi non-IT.
   - Menerima *early warning alert* jika performa anggota tim berada di bawah standar SLA.
3. **Karyawan (Individual Contributor):**
   - Melihat rincian capaian KPI per sprint beserta breakdown nilai tiap indikator.
   - Memantau grafik akumulasi performa tahunan dan statistik kontribusi (Jira/GitLab).

### 1.4 Fitur Utama (Core Features)
* **Dynamic KPI Rule Builder:** Modul GUI bagi Admin untuk menyusun formula matematika bebas, mengasosiasikan variabel dengan data Jira/GitLab/Manual, serta menentukan cap score (batas maksimal nilai).
* **Jira & GitLab Sync Service:** Worker otomatis yang menarik data active sprint, completed story points, commit counts, merged merge requests, dan bug count berdasarkan pemetaan email/username karyawan.
* **Safe Formula Calculation Engine:** Engine Python berbasis Abstract Syntax Tree (AST) untuk mengeksekusi rumus tanpa risiko *remote code execution*.
* **Sprint Performance & Cumulative Rollup:** Agregasi skor periodik (per-sprint) menjadi skor kumulatif bulanan, triwulanan (Q1-Q4), dan tahunan.
* **Multi-Division Support:** Manajemen role & template KPI bebas untuk divisi IT, Product, Marketing, Sales, HR, Finance.

---

## 2. Arsitektur Sistem & Tech Stack

### 2.1 Arsitektur High-Level
Sistem dibangun menggunakan pendekatan **Decoupled Architecture** yang memisahkan antara Presentation Layer (Frontend), API Service (Backend), Worker & Calculation Engine, serta Integrator Services.

```
+-----------------------------------------------------------------------+
|                         NEXT.JS FRONTEND                              |
|           (App Router, Tailwind CSS, Shadcn UI, Recharts)             |
+-----------------------------------+-----------------------------------+
                                    | REST API / JSON
                                    v
+-----------------------------------+-----------------------------------+
|                        FASTAPI BACKEND SERVICE                        |
|        (Authentication, Matrix Management, Analytics APIs)            |
+-----------------+---------------------------------+-------------------+
                  |                                 |
                  v                                 v
+-----------------+---------------+ +---------------+-------------------+
|     PYTHON KPI ENGINE           | |      CELERY / REDIS WORKERS       |
|  (AST Safe Evaluator, Rollup)   | |  (Jira Sync, GitLab Sync Cron)    |
+-----------------+---------------+ +---------------+-------------------+
                  |                                 |
                  +-----------------+---------------+
                                    |
                                    v
+-----------------------------------+-----------------------------------+
|                     POSTGRESQL DATABASE                               |
|        (Relational Data + JSONB Dynamic Rules & Raw Logs)             |
+-----------------------------------------------------------------------+
```

### 2.2 Rincian Tech Stack
* **Frontend:**
  * **Framework:** Next.js 14+ (React 18+, App Router, Server/Client Components).
  * **Styling:** Tailwind CSS + Shadcn UI (Radix Primitives).
  * **State Management & Fetching:** TanStack Query v5 (React Query) + Zustand.
  * **Visualization:** Recharts / Tremor (Chart Components).
  * **Icons & Form:** Lucide React, React Hook Form, Zod Schema Validation.
* **Backend & Engine:**
  * **Framework:** Python 3.11+ dengan FastAPI (Asynchronous Web Framework).
  * **ORM & Validation:** SQLAlchemy v2 (Async Engine) + Pydantic v2.
  * **Safe Math Engine:** Python Native `ast` (Abstract Syntax Tree) Parser.
  * **Task Queue / Scheduler:** Celery + Redis (Asynchronous background tasks & cron for Jira/GitLab sync).
* **Integrasi External:**
  * **Jira API:** Jira REST API v3 & Jira Agile API v1 (OAuth 2.0 / Personal Access Token).
  * **GitLab API:** GitLab REST API v4 (OAuth 2.0 / Personal Access Token / Webhooks).
* **Database & Storage:**
  * **Primary DB:** PostgreSQL 15+ (Native JSONB support for dynamic configs).
  * **Cache & Message Broker:** Redis 7+.

---

## 3. Database Schema & ERD

### 3.1 Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    DIVISIONS ||--o{ USERS : "has"
    DIVISIONS ||--o{ KPI_RULES : "defines"
    USERS ||--o{ SPRINT_KPI_SCORES : "receives"
    USERS ||--o{ CUMULATIVE_KPI_SCORES : "has accumulated"
    USERS ||--o{ RAW_METRICS_DATA : "generates"
    
    KPI_RULES ||--o{ KPI_RULE_METRICS : "contains"
    METRICS ||--o{ KPI_RULE_METRICS : "referenced in"
    
    SPRINTS ||--o{ RAW_METRICS_DATA : "belongs to"
    SPRINTS ||--o{ SPRINT_KPI_SCORES : "evaluated in"

    DIVISIONS {
        uuid id PK
        string code UK
        string name
        boolean is_active
    }

    USERS {
        uuid id PK
        uuid division_id FK
        string full_name
        string email UK
        string jira_account_id
        string gitlab_username
        string role
        boolean is_active
    }

    METRICS {
        uuid id PK
        string key UK
        string name
        string source_type
        string default_unit
    }

    KPI_RULES {
        uuid id PK
        uuid division_id FK
        string name
        integer version
        boolean is_active
    }

    KPI_RULE_METRICS {
        uuid id PK
        uuid kpi_rule_id FK
        uuid metric_id FK
        decimal weight
        string calc_type
        string formula_expression
        jsonb variables
        decimal cap_score
    }

    SPRINTS {
        uuid id PK
        string jira_sprint_id UK
        string sprint_name
        timestamp start_date
        timestamp end_date
        string status
    }

    RAW_METRICS_DATA {
        uuid id PK
        uuid user_id FK
        uuid sprint_id FK
        jsonb metrics_payload
        timestamp fetched_at
    }

    SPRINT_KPI_SCORES {
        uuid id PK
        uuid user_id FK
        uuid sprint_id FK
        uuid kpi_rule_id FK
        decimal final_score
        jsonb breakdown_details
        timestamp calculated_at
    }

    CUMULATIVE_KPI_SCORES {
        uuid id PK
        uuid user_id FK
        string period_type
        string period_key
        decimal average_score
        integer total_sprints
        timestamp calculated_at
    }
```

### 3.2 SQL DDL Schema (PostgreSQL)

```sql
-- Enable UUID Extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. TABLE: DIVISIONS
CREATE TABLE divisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. TABLE: USERS
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    division_id UUID NOT NULL REFERENCES divisions(id) ON DELETE RESTRICT,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    jira_account_id VARCHAR(100),
    gitlab_username VARCHAR(100),
    role VARCHAR(50) NOT NULL DEFAULT 'EMPLOYEE', -- 'ADMIN', 'LEAD', 'EMPLOYEE'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. TABLE: METRICS (Master Dictionary Indikator)
CREATE TABLE metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(100) NOT NULL UNIQUE, -- e.g., 'jira_sp', 'gitlab_mr', 'bugs_count'
    name VARCHAR(150) NOT NULL,
    source_type VARCHAR(50) NOT NULL, -- 'JIRA', 'GITLAB', 'MANUAL'
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. TABLE: KPI_RULES (Rule Master Per Divisi)
CREATE TABLE kpi_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    division_id UUID NOT NULL REFERENCES divisions(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    version INT NOT NULL DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_division_version UNIQUE(division_id, version)
);

-- 5. TABLE: KPI_RULE_METRICS (Detail Matriks & Formula Dinamis)
CREATE TABLE kpi_rule_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    kpi_rule_id UUID NOT NULL REFERENCES kpi_rules(id) ON DELETE CASCADE,
    metric_id UUID NOT NULL REFERENCES metrics(id) ON DELETE RESTRICT,
    weight NUMERIC(5, 4) NOT NULL, -- e.g. 0.4000 = 40%
    calc_type VARCHAR(50) NOT NULL DEFAULT 'FORMULA', -- 'FORMULA', 'DIRECT'
    formula_expression TEXT NOT NULL, -- e.g. "min((jira_sp / target_sp) * 100, 120) - (bugs * 10)"
    variables JSONB DEFAULT '{}'::jsonb, -- e.g. {"target_sp": 20}
    cap_score NUMERIC(5, 2) DEFAULT 120.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. TABLE: SPRINTS
CREATE TABLE sprints (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    jira_sprint_id VARCHAR(100) UNIQUE,
    sprint_name VARCHAR(150) NOT NULL,
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE', -- 'ACTIVE', 'CLOSED', 'FUTURE'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. TABLE: RAW_METRICS_DATA (Hasil Fetch API Jira & GitLab Raw)
CREATE TABLE raw_metrics_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sprint_id UUID NOT NULL REFERENCES sprints(id) ON DELETE CASCADE,
    metrics_payload JSONB NOT NULL DEFAULT '{}'::jsonb, -- {"jira_sp": 22, "gitlab_mr": 5, "bugs": 1}
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_user_sprint_raw UNIQUE(user_id, sprint_id)
);

-- 8. TABLE: SPRINT_KPI_SCORES (Hasil Kalkulasi Engine Per Sprint)
CREATE TABLE sprint_kpi_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sprint_id UUID NOT NULL REFERENCES sprints(id) ON DELETE CASCADE,
    kpi_rule_id UUID NOT NULL REFERENCES kpi_rules(id) ON DELETE RESTRICT,
    final_score NUMERIC(5, 2) NOT NULL,
    breakdown_details JSONB NOT NULL, -- Detail hitungan per matriks
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_user_sprint_score UNIQUE(user_id, sprint_id)
);

-- 9. TABLE: CUMULATIVE_KPI_SCORES (Hasil Agregasi Kumulatif)
CREATE TABLE cumulative_kpi_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    period_type VARCHAR(20) NOT NULL, -- 'MONTHLY', 'QUARTERLY', 'YEARLY'
    period_key VARCHAR(20) NOT NULL,  -- e.g. '2026-Q1', '2026'
    average_score NUMERIC(5, 2) NOT NULL,
    total_sprints INT NOT NULL,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_user_period UNIQUE(user_id, period_type, period_key)
);

-- INDEXES FOR PERFORMANCE
CREATE INDEX idx_users_division ON users(division_id);
CREATE INDEX idx_raw_metrics_user_sprint ON raw_metrics_data(user_id, sprint_id);
CREATE INDEX idx_sprint_scores_user ON sprint_kpi_scores(user_id);
CREATE INDEX idx_cumulative_scores_user ON cumulative_kpi_scores(user_id, period_key);
```

---

## 4. Integrasi API Jira & GitLab

### 4.1 Strategi User Mapping
Sistem mencocokkan identitas karyawan menggunakan **Email Address** sebagai *Primary Identifier*:
1. **Jira:** Di-mapping menggunakan `jira_account_id` yang didapat melalui endpoint Jira User API berdasarkan email.
2. **GitLab:** Di-mapping menggunakan `gitlab_username` yang terhubung dengan email akun kantor GitLab.

---

### 4.2 Spesifikasi Integrasi Jira API

#### Endpoint yang Digunakan:
1. **Get Active Sprints from Board:**
   - `GET /rest/agile/1.0/board/{boardId}/sprint?state=active`
2. **Get Issues in Sprint:**
   - `GET /rest/agile/1.0/sprint/{sprintId}/issue?jql=assignee={accountId}`

#### Parameter Metrics Extracted:
* `jira_sp` (Completed Story Points): Penjumlahan nilai Story Points dari tiket yang berstatus `Done` / `Closed` pada sprint tersebut.
* `jira_issues_completed`: Jumlah tiket completed.
* `bugs_reported`: Jumlah tiket tipe `Bug` yang dimasukkan atau ditujukan pada assignee selama siklus sprint.

---

### 4.3 Spesifikasi Integrasi GitLab API

#### Endpoint yang Digunakan:
1. **Get Merged Merge Requests (MR):**
   - `GET /api/v4/merge_requests?author_username={username}&state=merged&created_after={sprint_start}&created_before={sprint_end}`
2. **Get Commits Count:**
   - `GET /api/v4/users/{username}/events?action=pushed&after={sprint_start}&before={sprint_end}`
3. **Get Code Review Comments / Approvals:**
   - `GET /api/v4/merge_requests?approver_usernames[]={username}&updated_after={sprint_start}`

#### Parameter Metrics Extracted:
* `gitlab_mr_merged`: Total Merge Request buatan karyawan yang berhasil di-merge ke branch utama (`main`/`master`/`develop`).
* `gitlab_commits`: Total commit yang didorong selama periode sprint.
* `gitlab_reviews`: Total keterlibatan sebagai reviewer atau approver MR rekan tim.

---

## 5. Python Dynamic KPI Engine (AST Safe Evaluator)

Berikut adalah implementasi lengkap engine penilaian KPI berbasis Python menggunakan `ast` untuk keamanan total dan fleksibilitas rumus matematika bebas dari JSON.

```python
import ast
import operator
from typing import Dict, Any, List

class SafeMathEvaluator(ast.NodeVisitor):
    ALLOWED_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    ALLOWED_FUNCTIONS = {
        "min": min,
        "max": max,
        "abs": abs,
        "round": round
    }

    def __init__(self, context: Dict[str, float]):
        self.context = context

    def visit(self, node):
        if isinstance(node, ast.Expression):
            return self.visit(node.body)

        elif isinstance(node, (ast.Constant, ast.Num)):
            return float(node.value if isinstance(node, ast.Constant) else node.n)

        elif isinstance(node, ast.Name):
            if node.id in self.context:
                return float(self.context[node.id])
            raise ValueError(f"Variabel '{node.id}' tidak ditemukan dalam context metrics!")

        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type in self.ALLOWED_OPERATORS:
                left = self.visit(node.left)
                right = self.visit(node.right)
                if op_type == ast.Div and right == 0:
                    return 0.0
                return self.ALLOWED_OPERATORS[op_type](left, right)
            raise ValueError(f"Operator biner '{op_type.__name__}' tidak diizinkan!")

        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type in self.ALLOWED_OPERATORS:
                return self.ALLOWED_OPERATORS[op_type](self.visit(node.operand))
            raise ValueError(f"Operator unary '{op_type.__name__}' tidak diizinkan!")

        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in self.ALLOWED_FUNCTIONS:
                func = self.ALLOWED_FUNCTIONS[node.func.id]
                args = [self.visit(arg) for arg in node.args]
                return float(func(*args))
            raise ValueError("Pemanggilan fungsi tidak dikenal/diizinkan!")

        else:
            raise ValueError(f"Sintaks tidak diizinkan dalam rumus: {type(node).__name__}")


def evaluate_kpi_formula(formula_str: str, context: Dict[str, float]) -> float:
    try:
        tree = ast.parse(formula_str, mode='eval')
        evaluator = SafeMathEvaluator(context)
        return float(evaluator.visit(tree))
    except Exception as e:
        print(f"[KPI Engine Error] Gagal mengevaluasi formula '{formula_str}': {str(e)}")
        return 0.0


class DynamicKPIEngine:
    @classmethod
    def calculate_sprint_score(
        cls, 
        rule_config: Dict[str, Any], 
        raw_metrics: Dict[str, float]
    ) -> Dict[str, Any]:
        
        total_kpi_score = 0.0
        breakdown = []

        metrics_list = rule_config.get("metrics", [])
        
        for metric_rule in metrics_list:
            metric_key = metric_rule["key"]
            weight = float(metric_rule["weight"])
            formula = metric_rule["formula_expression"]
            variables = metric_rule.get("variables", {})
            cap_score = metric_rule.get("cap_score", 120.0)

            eval_context = {**raw_metrics, **variables}
            raw_calculated_score = evaluate_kpi_formula(formula, eval_context)
            capped_score = min(max(raw_calculated_score, 0.0), cap_score)

            weighted_score = capped_score * weight
            total_kpi_score += weighted_score

            breakdown.append({
                "metric_key": metric_key,
                "formula_used": formula,
                "input_variables": eval_context,
                "raw_score": round(raw_calculated_score, 2),
                "capped_score": round(capped_score, 2),
                "weight": weight,
                "weighted_score": round(weighted_score, 2)
            })

        return {
            "division_id": rule_config.get("division_id"),
            "kpi_rule_id": rule_config.get("rule_id"),
            "final_sprint_score": round(total_kpi_score, 2),
            "breakdown": breakdown
        }

    @classmethod
    def calculate_cumulative_score(cls, sprint_scores: List[float]) -> Dict[str, Any]:
        if not sprint_scores:
            return {"cumulative_score": 0.0, "total_sprints": 0}

        avg_score = sum(sprint_scores) / len(sprint_scores)
        return {
            "cumulative_score": round(avg_score, 2),
            "total_sprints": len(sprint_scores)
        }


if __name__ == "__main__":
    it_developer_rule = {
        "rule_id": "rule-it-dev-v1",
        "division_id": "div-it-01",
        "metrics": [
            {
                "key": "jira_sp",
                "weight": 0.40,
                "formula_expression": "min((jira_sp / target_sp) * 100, 120)",
                "variables": {"target_sp": 20},
                "cap_score": 120.0
            },
            {
                "key": "gitlab_mr",
                "weight": 0.40,
                "formula_expression": "(gitlab_mr_merged / target_mr) * 100",
                "variables": {"target_mr": 5},
                "cap_score": 100.0
            },
            {
                "key": "bugs_deduction",
                "weight": 0.20,
                "formula_expression": "max(100 - (bugs_count * 15), 0)",
                "variables": {},
                "cap_score": 100.0
            }
        ]
    }

    employee_sprint_1_data = {
        "jira_sp": 22,
        "gitlab_mr_merged": 4,
        "bugs_count": 1
    }

    sprint_result = DynamicKPIEngine.calculate_sprint_score(it_developer_rule, employee_sprint_1_data)
    print("=== HASIL SPRINT SCORE ===")
    print(sprint_result)

    sprint_history = [sprint_result["final_sprint_score"], 92.5, 88.0, 95.0]
    cumulative_result = DynamicKPIEngine.calculate_cumulative_score(sprint_history)
    print("
=== HASIL AKUMULASI PERFORMA ===")
    print(cumulative_result)
```

---

## 6. Next.js Frontend Architecture & API Specs

### 6.1 Structure Folder Project (Next.js 14 App Router)

```
kpi-dashboard-frontend/
├── src/
│   ├── app/
│   │   ├── (auth)/
│   │   │   └── login/
│   │   ├── (dashboard)/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx                    # Overview Dashboard
│   │   │   ├── sprint-performance/
│   │   │   │   └── page.tsx                # Report Per Sprint
│   │   │   ├── cumulative-performance/
│   │   │   │   └── page.tsx                # Report Akumulasi Karyawan
│   │   │   ├── matrix-configurator/
│   │   │   │   └── page.tsx                # Form Aturan Matriks Dynamic (Admin)
│   │   │   └── users/
│   │   │       └── page.tsx
│   ├── components/
│   │   ├── ui/                             # Shadcn UI Base Components
│   │   ├── charts/
│   │   │   ├── SprintTrendChart.tsx        # Line Chart Akumulasi
│   │   │   └── BreakdownRadarChart.tsx     # Radar Chart Per Indikator
│   │   ├── forms/
│   │   │   └── RuleMetricForm.tsx          # Dynamic Formula Builder
│   │   └── shared/
│   │       ├── Header.tsx
│   │       └── Sidebar.tsx
│   ├── lib/
│   │   ├── api-client.ts                   # Axios / Fetch Wrapper
│   │   └── utils.ts
│   ├── services/
│   │   ├── kpiService.ts
│   │   ├── jiraService.ts
│   │   └── userService.ts
│   └── types/
│       └── kpi.ts
├── public/
├── package.json
└── tailwind.config.js
```

---

### 6.2 Frontend Screen Architecture

#### 1. Sprint Performance Dashboard (`/sprint-performance`)
* **Header Filter:** Dropdown Select Divisi, Select Sprint Active/Historical, & Search Karyawan.
* **Metric Cards:** Average Team Score, Top Performer, Total Completed Story Points, Total MR Merged.
* **Performance Table:**
  * Kolom: Nama Karyawan | Divisi | Story Points | GitLab MR | Bug Count | Raw Score | **Final Weighted Score** | Status.
  * *Expandable Row:* Menampilkan breakdown rumus dan nilai individual per indikator.

#### 2. Cumulative Performance View (`/cumulative-performance`)
* **Period Switcher:** Quarter View (Q1, Q2, Q3, Q4) vs Year-to-Date (YTD).
* **Trend Line Chart:** Grafik pergerakan nilai rata-rata KPI karyawan dari Sprint 1 hingga Sprint N.
* **Leaderboard Widget:** Ranking performa individu beserta indicator badge (Up/Down Trend).

#### 3. Matrix Configurator (`/matrix-configurator`)
* **Admin GUI:**
  * Form pembuatan Aturan KPI per Divisi.
  * **Dynamic Formula Input:** User dapat mengetik rumus bebas seperti `min((jira_sp / target_sp) * 100, 120) - (bugs * 10)`.
  * **Formula Live Tester:** Fitur tes input dummy untuk memastikan rumus valid sebelum disimpan ke database.

---

### 6.3 REST API Endpoints Specification

#### 1. KPI Configuration Endpoints
* `GET /api/v1/kpi-rules?division_id={id}`
  * **Desc:** Mengambil aturan matriks KPI aktif untuk divisi tertentu.
* `POST /api/v1/kpi-rules`
  * **Desc:** Menyimpan konfigurasi matriks dan rumus dinamis baru.
  * **Payload Request:**
    ```json
    {
      "division_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "name": "IT Developer Matrix 2026",
      "metrics": [
        {
          "metric_key": "jira_sp",
          "weight": 0.40,
          "calc_type": "FORMULA",
          "formula_expression": "min((jira_sp / target_sp) * 100, 120)",
          "variables": {"target_sp": 20},
          "cap_score": 120
        }
      ]
    }
    ```

#### 2. Calculation & Report Endpoints
* `POST /api/v1/kpi/calculate-sprint/{sprint_id}`
  * **Desc:** Memicu background worker untuk menarik data API Jira/GitLab, menghitung skor dengan Python Engine, dan menyimpan ke DB.
* `GET /api/v1/kpi/reports/sprint/{sprint_id}`
  * **Desc:** Mengambil laporan nilai KPI seluruh karyawan untuk sprint tertentu.
* `GET /api/v1/kpi/reports/cumulative?user_id={id}&period_type=QUARTERLY&period_key=2026-Q1`
  * **Desc:** Mengambil akumulasi performa dan histori nilai sprint karyawan.

---

## 7. Panduan Deployment & Operasional

### 7.1 Prasyarat Lingkungan (Prerequisites)
* Docker & Docker Compose
* Node.js v18+ & pnpm / npm
* Python 3.11+
* PostgreSQL 15+ & Redis 7+

### 7.2 Docker Compose Quickstart (`docker-compose.yml`)

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: kpi_db
      POSTGRES_USER: kpi_user
      POSTGRES_PASSWORD: kpi_password
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://kpi_user:kpi_password@postgres:5432/kpi_db
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  worker:
    build: ./backend
    command: celery -A app.worker.celery_app worker --loglevel=info
    environment:
      DATABASE_URL: postgresql+asyncpg://kpi_user:kpi_password@postgres:5432/kpi_db
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000/api/v1
    depends_on:
      - backend

volumes:
  pgdata:
```
