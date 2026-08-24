import json
import os
import re
import time
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
from typing import Any, Dict, List, Optional

logger = logging.getLogger("feature_analyzer")

# Minimal .env reader (no python-dotenv dependency). Reads backend/.env so
# ZAI_* work locally; environment variables always take precedence
# (Railway sets them natively in production).
_DOTENV_CACHE = None


def _load_dotenv_once() -> dict:
    global _DOTENV_CACHE
    if _DOTENV_CACHE is not None:
        return _DOTENV_CACHE
    data = {}
    try:
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    data[k.strip()] = v.strip()
    except Exception:  # noqa: BLE001
        pass
    _DOTENV_CACHE = data
    return data


def _get_env(key: str, default: str = "") -> str:
    val = os.getenv(key)
    if val:
        return val
    return _load_dotenv_once().get(key, default)

# Default 5-pillar caps + total->kpi_points mapping. When a feature_complexity
# KPIRuleMetric provides its own variables, resolve_feature_config() overrides
# these so scoring stays config-driven from the Configurator matrix.
DEFAULT_FEATURE_CONFIG = {
    "max_c": 5,
    "max_i": 5,
    "max_s": 5,
    "max_r": 3,
    "max_o": 2,
    # sorted descending list of [min_total, points]
    "point_map": [
        [18, 25.0],
        [15, 20.0],
        [12, 15.0],
        [9, 10.0],
        [6, 7.0],
        [3, 4.0],
        [0, 1.0],
    ],
}

# Keyword groups used by the deterministic scorer. Overridable wholesale via env
# FEATURE_RULE_KEYWORDS_JSON ({"group_name": ["kw1", "kw2", ...]}) so rules can
# be tuned in production without a code change. Each group falls back to the
# built-in defaults below.
_DEFAULT_KEYWORDS = {
    "routine": [
        'upload gc', 'upload bca', 'generate report', 'test support', 'private event support',
        'public event support', 'update banner', 'good morning', 'create username', 'password for test',
        'configure and prepare for test', 'prod - test', 'minor fix', 'text change',
    ],
    "rebuild": [
        'build ulang', 'rebuild', '16kb', '16 kb', 'arm compatibility', 'native-bridge',
        'jni', 'ndk', 'recompile', 'page size alignment', 'memory alignment',
    ],
    "core": [
        'squash', 'refactor core', 'architecture overhaul', 'framework upgrade',
        'zero-downtime', 'migration', 'blue-green',
    ],
    "db_migration": [
        'schema migration', 'alter table', 'indexing', 'postgresql query optimization',
        'foreign key', 'database constraint', 'db setup',
    ],
    "zero_downtime": [
        'zero-downtime deployment', 'nginx blue-green config', 'pipeline automation',
        'sentry security monitoring',
    ],
    "security": [
        'owasp testing', 'penetration scanning', 'xss mitigation', 'csrf protection',
        'security hardening',
    ],
    "high_impact_business": [
        'doku', 'kredivo', 'payment', 'booking', 'overtime', 'roster',
        'leave submission', 'quota management',
    ],
    "medium_impact_business": ['reporting', 'report', 'event support', 'travel fair'],
    "low_impact_business": ['theme option', 'styling', 'logo', 'aria-label'],
    "high_scope": ['api integration', 'data sync', 'deployment', 'db setup'],
    "medium_scope": ['doku', 'kredivo', 'payment gateway', 'prometheus', 'expiry check'],
    "low_scope": ['overtime order', 'leave request', 'roster alert', 'report generate'],
    "high_risk": ['overtime', 'leave submission', 'roster', 'api integration', 'data sync', 'payment gateway'],
}

_OVERRIDE_KEYWORDS = None


def _load_keyword_config() -> dict:
    global _OVERRIDE_KEYWORDS
    if _OVERRIDE_KEYWORDS is None:
        raw = _get_env("FEATURE_RULE_KEYWORDS_JSON", "")
        parsed = {}
        if raw:
            try:
                parsed = json.loads(raw)
            except Exception:  # noqa: BLE001
                logger.warning("FEATURE_RULE_KEYWORDS_JSON is invalid JSON; using built-in defaults")
        _OVERRIDE_KEYWORDS = parsed if isinstance(parsed, dict) else {}
    return _OVERRIDE_KEYWORDS


def _kw(name: str, default: list) -> list:
    """Return the configured keyword list for a group, else the default."""
    override = _load_keyword_config().get(name)
    if isinstance(override, list) and override:
        return [str(k).lower() for k in override]
    return default

PROMPT_VERSION = "v1"


def _normalise_config(cfg: Optional[dict]) -> dict:
    merged = dict(DEFAULT_FEATURE_CONFIG)
    if cfg:
        for k in ("max_c", "max_i", "max_s", "max_r", "max_o"):
            if k in cfg and cfg[k] is not None:
                merged[k] = int(cfg[k])
        pm = cfg.get("point_map")
        if isinstance(pm, list) and pm:
            merged["point_map"] = [[int(a), float(b)] for a, b in pm]
    return merged


def kpi_points_from_total(total_score: float, config: Optional[dict] = None) -> float:
    """Map a raw total score (0..20) to KPI points using the config point_map."""
    cfg = _normalise_config(config)
    for min_total, points in cfg["point_map"]:
        if total_score >= min_total:
            return float(points)
    return cfg["point_map"][-1][1] if cfg["point_map"] else 1.0


def _summary_hash(summary: str) -> str:
    """Stable content hash for a summary, used as persistent-cache key."""
    return sha256((summary or "").strip().encode("utf-8")).hexdigest()


def analyze_multi_factor(issue_data: dict, config: Optional[dict] = None) -> dict:
    """
    Detailed Multi-Factor Scoring Analyzer for Jira Issues (deterministic rules).
    Returns:
        - technical_complexity (0-5)
        - business_impact (0-5)
        - system_scope (0-5)
        - delivery_risk (0-3)
        - ownership_level (0-2)
        - total_score (0-20)
        - kpi_points (1.0 - 25.0)
    """
    cfg = _normalise_config(config)
    max_c, max_i, max_s, max_r, max_o = (cfg[k] for k in ("max_c", "max_i", "max_s", "max_r", "max_o"))

    fields = issue_data.get('fields', {}) if issue_data else {}
    summary = (fields.get('summary') or '').strip().lower()

    raw_desc = fields.get('description') or ''
    desc_text = ''
    if isinstance(raw_desc, str):
        desc_text = raw_desc.lower()
    elif isinstance(raw_desc, dict):
        desc_text = str(raw_desc).lower()

    combined_text = f"{summary} {desc_text}"
    issuetype = (fields.get('issuetype') or {}).get('name', 'Task').lower()
    subtasks = fields.get('subtasks', [])
    subtask_cnt = len(subtasks) if isinstance(subtasks, list) else 0
    story_points = float(issue_data.get('story_points') or 0.0)

    # 0. Check QA/Testing Verification Task
    is_qa = summary.startswith('qa:') or 'qa test' in combined_text or 'test case' in combined_text or summary.startswith('testing')

    # 1. Check Routine operational task
    routine_keywords = _kw("routine", _DEFAULT_KEYWORDS["routine"])
    is_routine = any(kw in combined_text for kw in routine_keywords)

    # 2. Check Rebuild / Core Engineering
    is_rebuild = any(kw in combined_text for kw in _kw("rebuild", _DEFAULT_KEYWORDS["rebuild"]))
    is_core = any(kw in combined_text for kw in _kw("core", _DEFAULT_KEYWORDS["core"]))

    # Deep Analysis of Description & Summary for Architectural Complexity
    has_db_migration = any(kw in combined_text for kw in _kw("db_migration", _DEFAULT_KEYWORDS["db_migration"]))
    has_zero_downtime = any(kw in combined_text for kw in _kw("zero_downtime", _DEFAULT_KEYWORDS["zero_downtime"]))
    has_security_remediation = any(kw in combined_text for kw in _kw("security", _DEFAULT_KEYWORDS["security"]))

    # === DIMENSION 1: Technical Complexity (0-max_c) ===
    if is_routine:
        complexity = 1
    elif is_qa:
        complexity = 2 if ('automation' in combined_text or 'regression' in combined_text or 'security' in combined_text or has_security_remediation) else 1
    elif is_rebuild:
        complexity = max_c
    elif is_core:
        complexity = 4
    elif has_db_migration or has_zero_downtime:
        complexity = 4
    elif 'epic' in issuetype:
        complexity = max_c
    elif 'story' in issuetype:
        complexity = 3
    elif 'bug' in issuetype:
        complexity = 2
    else:
        complexity = 2

    if not is_qa and not is_routine:
        if subtask_cnt >= 8:
            complexity = max(complexity, max_c)
        elif subtask_cnt >= 4:
            complexity = max(complexity, 4)
        elif story_points >= 8:
            complexity = min(complexity + 1, max_c)

    # === DIMENSION 2: Business Impact (0-max_i) ===
    if is_routine:
        impact = 1
    elif is_qa:
        impact = 2 if ('automation' in combined_text or 'security' in combined_text or has_security_remediation) else 1
    elif is_rebuild:
        impact = max_i
    elif is_core or has_zero_downtime:
        impact = max_i
    elif has_db_migration or has_security_remediation:
        impact = 4
    elif any(kw in combined_text for kw in _kw("high_impact_business", _DEFAULT_KEYWORDS["high_impact_business"])):
        impact = 4
    elif any(kw in combined_text for kw in _kw("medium_impact_business", _DEFAULT_KEYWORDS["medium_impact_business"])):
        impact = 3
    elif any(kw in combined_text for kw in _kw("low_impact_business", _DEFAULT_KEYWORDS["low_impact_business"])):
        impact = 2
    else:
        impact = 2

    # === DIMENSION 3: System Scope (0-max_s) ===
    if is_routine:
        scope = 0
    elif is_qa:
        scope = 1
    elif is_rebuild:
        scope = max_s
    elif is_core or has_zero_downtime:
        scope = 4
    elif has_db_migration:
        scope = 3
    elif any(kw in combined_text for kw in _kw("high_scope", _DEFAULT_KEYWORDS["high_scope"])):
        scope = 4
    elif any(kw in combined_text for kw in _kw("medium_scope", _DEFAULT_KEYWORDS["medium_scope"])):
        scope = 3
    elif any(kw in combined_text for kw in _kw("low_scope", _DEFAULT_KEYWORDS["low_scope"])):
        scope = 2
    else:
        scope = 2

    # === DIMENSION 4: Delivery Risk (0-max_r) ===
    if is_routine:
        risk = 0
    elif is_qa:
        risk = 1
    elif is_rebuild or is_core or has_zero_downtime:
        risk = max_r
    elif has_db_migration or has_security_remediation:
        risk = 2
    elif any(kw in combined_text for kw in _kw("high_risk", _DEFAULT_KEYWORDS["high_risk"])):
        risk = 2
    else:
        risk = 1

    # === DIMENSION 5: Ownership Level (0-max_o) ===
    if is_qa or is_routine:
        ownership = 0
    elif is_rebuild:
        ownership = max_o
    elif subtask_cnt >= 5 or story_points >= 8:
        ownership = max_o
    else:
        ownership = 1

    total_score = min(complexity + impact + scope + risk + ownership, max_c + max_i + max_s + max_r + max_o)
    kpi_points = kpi_points_from_total(total_score, cfg)

    return {
        "technical_complexity": complexity,
        "business_impact": impact,
        "system_scope": scope,
        "delivery_risk": risk,
        "ownership_level": ownership,
        "total_score": total_score,
        "kpi_points": kpi_points,
    }


def calculate_feature_weight(issue_data: dict, config: Optional[dict] = None) -> float:
    """Legacy entrypoint kept for backward compatibility (rules-based)."""
    res = analyze_multi_factor(issue_data, config=config)
    return res["kpi_points"]


# ---------------------------------------------------------------------------
# Pluggable FeatureScorer (rules / LLM via Z.AI Coding Plan)
# ---------------------------------------------------------------------------

class LLMFeatureScorer:
    """Scores Jira issues with an external LLM through Z.AI GLM Coding Plan.

    - Strict JSON output (5 dimensions + total + reasoning).
    - Retries + per-issue caching; falls back to the rules scorer on failure.
    - Config-driven caps & point mapping.
    """

    DEFAULT_BASE_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, config: Optional[dict] = None, timeout: Optional[int] = None):
        self.api_key = api_key or _get_env("ZAI_API_KEY")
        self.model = model or _get_env("ZAI_MODEL") or "glm-5.3"
        self.base_url = _get_env("ZAI_BASE_URL") or self.DEFAULT_BASE_URL
        self.config = _normalise_config(config)
        self.timeout = timeout or int(_get_env("ZAI_TIMEOUT_SECONDS", "120") or "120")
        self.cache: Dict[str, dict] = {}
        # Sliding-window rate limit + per-run budget (env: LLM_RPM, LLM_MAX_ISSUES_PER_SYNC)
        self._call_times: List[float] = []
        self._llm_calls = 0

    def _payload_for(self, issue_data: dict) -> dict:
        fields = issue_data.get('fields', {}) if issue_data else {}
        summary = fields.get('summary') or ''
        desc = fields.get('description') or ''
        if isinstance(desc, dict):
            desc = str(desc)
        issuetype = (fields.get('issuetype') or {}).get('name', 'Task')
        issue_key = issue_data.get('key') or ''
        story_points = issue_data.get('story_points')
        subtask_cnt = len(fields.get('subtasks', [])) if isinstance(fields.get('subtasks', []), list) else 0
        project = (fields.get('project') or {}).get('key') or (issue_key.split('-')[0] if issue_key else '')

        cfg = self.config
        schema = {
            "technical_complexity": f"integer 0..{cfg['max_c']}",
            "business_impact": f"integer 0..{cfg['max_i']}",
            "system_scope": f"integer 0..{cfg['max_s']}",
            "delivery_risk": f"integer 0..{cfg['max_r']}",
            "ownership_level": f"integer 0..{cfg['max_o']}",
            "reasoning": "short justification (max 40 words)",
        }
        system = (
            "You are a senior engineering manager scoring Jira issues on 5 dimensions "
            "for a company KPI system. Score strictly per the schema and rules provided. "
            "Respond with ONLY valid JSON, no markdown fences.\n"
            "Rules:\n"
            "- Routine/support tasks (uploads, banner text changes, minor fixes, QA test runs) "
            "get LOW complexity/impact/scope.\n"
            "- Platform rebuilds, core refactors, DB migrations, zero-downtime deployments get "
            "HIGH complexity (5), HIGH impact (>=4), HIGH scope (>=4) and HIGH delivery risk (>=2).\n"
            "- Issues touching payments, overtime/roster, quota management, or customer-facing "
            "business flows get business_impact >= 3.\n"
            "- A bug without context gets complexity 2, impact 2, scope 2, risk 1, ownership 1.\n"
            "- Scale ownership by who drives the work: full ownership (epic owner, 5+ subtasks, "
            "large scope) = max; clear solo deliverable = mid; pure QA/routine = 0.\n"
            "- Avoid 0 on a dimension unless the task is truly trivial on that axis; a moderate "
            "task should sit in the 2-4 band, not the extremes.\n"
            f"Return JSON with keys: {', '.join(schema.keys())} where "
            f"technical_complexity is {schema['technical_complexity']}, "
            f"business_impact is {schema['business_impact']}, "
            f"system_scope is {schema['system_scope']}, "
            f"delivery_risk is {schema['delivery_risk']}, "
            f"ownership_level is {schema['ownership_level']}, and reasoning is a short string."
        )
        user = (
            f"Jira issue {issue_key or '<no key>'} (project: {project or 'unknown'}, "
            f"type: {issuetype or 'Task'})\n"
            f"Summary: {summary or '-'}\n"
            f"Story points: {story_points if story_points is not None else '-'}\n"
            f"Subtask count: {subtask_cnt}\n"
            f"Description:\n{desc or '-'}"
        )
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }

    @staticmethod
    def _parse_json(text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        return json.loads(text)

    def _normalise_result(self, parsed: dict, fallback: dict) -> dict:
        cfg = self.config
        caps = {"technical_complexity": cfg["max_c"], "business_impact": cfg["max_i"],
                "system_scope": cfg["max_s"], "delivery_risk": cfg["max_r"],
                "ownership_level": cfg["max_o"]}
        out = {}
        for key, cap in caps.items():
            try:
                out[key] = max(0, min(int(parsed.get(key, 0)), cap))
            except (TypeError, ValueError):
                out[key] = fallback[key]
        total = min(sum(out.values()), sum(caps.values()))
        out["total_score"] = total
        out["kpi_points"] = kpi_points_from_total(total, cfg)
        out["reasoning"] = str(parsed.get("reasoning", ""))[:500]
        return out

    def _call_once(self, payload: dict) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        resp = requests.post(self.base_url, json=payload, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return self._parse_json(content)

    # -- rate limit / budget -------------------------------------------------
    def _rate_limit(self):
        """Sliding-window throttle for LLM calls (env LLM_RPM, default 10)."""
        rpm = int(_get_env("LLM_RPM", "10") or "10")
        if rpm <= 0:
            return
        now = time.time()
        self._call_times = [t for t in self._call_times if now - t < 60.0]
        if len(self._call_times) >= rpm:
            wait = 60.0 - (now - self._call_times[0])
            if wait > 0:
                time.sleep(wait)
            now = time.time()
        self._call_times.append(now)

    def _budget_exhausted(self) -> bool:
        limit = int(_get_env("LLM_MAX_ISSUES_PER_SYNC", "0") or "0")
        return limit > 0 and self._llm_calls >= limit

    # -- persistent cache ----------------------------------------------------
    def _db_get(self, issue_key: str, summary_hash: str):
        try:
            import models
            from database import SessionLocal
            from sqlalchemy import and_
            s = SessionLocal()
            try:
                return s.query(models.FeatureScoreCache).filter(
                    and_(
                        models.FeatureScoreCache.issue_key == issue_key,
                        models.FeatureScoreCache.summary_hash == summary_hash,
                    )
                ).first()
            finally:
                s.close()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"FeatureScoreCache read failed: {e}")
            return None

    def _db_set(self, issue_key: str, summary_hash: str, score: dict):
        try:
            import models
            from database import SessionLocal
            from sqlalchemy import and_
            s = SessionLocal()
            try:
                row = s.query(models.FeatureScoreCache).filter(
                    and_(
                        models.FeatureScoreCache.issue_key == issue_key,
                        models.FeatureScoreCache.summary_hash == summary_hash,
                    )
                ).first()
                if row is None:
                    row = models.FeatureScoreCache(
                        issue_key=issue_key,
                        summary_hash=summary_hash,
                        score=score,
                        model=score.get("model"),
                        score_type=score.get("score_type"),
                    )
                    s.add(row)
                else:
                    row.score = score
                    row.model = score.get("model")
                    row.score_type = score.get("score_type")
                s.commit()
            except Exception:  # noqa: BLE001
                s.rollback()
            finally:
                s.close()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"FeatureScoreCache write failed: {e}")

    def score(self, issue_data: dict) -> dict:
        """Score one issue. Returns the standard detail dict + score_type/model."""
        issue_key = issue_data.get('key') or ''
        summary = str(issue_data.get('fields', {}).get('summary', '') or '')
        summary_hash = _summary_hash(summary)
        mem_key = f"{issue_key}|{summary_hash}"

        if mem_key in self.cache:
            cached = dict(self.cache[mem_key])
            cached["score_type"] = "llm_cached"
            return cached

        fallback = analyze_multi_factor(issue_data, config=self.config)

        # Persistent cache (survives restarts; a rescore of unchanged issues
        # never pays the LLM again).
        row = self._db_get(issue_key, summary_hash)
        if row is not None and row.score:
            res = dict(row.score)
            res["score_type"] = row.score_type or "llm_cached"
            self.cache[mem_key] = res
            return res

        # Per-run LLM budget (env LLM_MAX_ISSUES_PER_SYNC).
        if self._budget_exhausted():
            fallback["score_type"] = "rules_budget"
            return fallback

        payload = self._payload_for(issue_data)
        last_err = None
        for attempt in range(3):
            try:
                self._rate_limit()
                self._llm_calls += 1
                parsed = self._call_once(payload)
                res = self._normalise_result(parsed, fallback)
                res["score_type"] = "llm"
                res["model"] = self.model
                res["prompt_version"] = PROMPT_VERSION
                self.cache[mem_key] = res
                self._db_set(issue_key, summary_hash, res)
                return res
            except Exception as e:  # noqa: BLE001
                last_err = e
                time.sleep(1.5 * (attempt + 1))
        logger.warning(f"LLM scoring failed ({last_err}), using rules fallback for {issue_key}")
        fallback["score_type"] = "rules_fallback"
        return fallback


class FeatureScorer:
    """High-level scorer: uses LLM when configured, otherwise deterministic rules."""

    def __init__(self, config: Optional[dict] = None, use_llm: Optional[bool] = None,
                 api_key: Optional[str] = None, model: Optional[str] = None):
        self.config = _normalise_config(config)
        llm_enabled = bool((api_key or _get_env("ZAI_API_KEY")).strip())
        if use_llm is None:
            use_llm = llm_enabled
        # use_llm=True always constructs the LLM scorer; it will fall back to rules
        # at call time if the API key is unusable.
        self.llm = None
        if use_llm:
            self.llm = LLMFeatureScorer(api_key=api_key, model=model, config=self.config)

    @property
    def mode(self) -> str:
        return "llm" if self.llm else "rules"

    def score(self, issue_data: dict) -> dict:
        if self.llm:
            res = self.llm.score(issue_data)
        else:
            res = analyze_multi_factor(issue_data, config=self.config)
            res["score_type"] = "rules"
        return res


def score_issue(issue_data: dict, scorer: Optional[FeatureScorer] = None, config: Optional[dict] = None) -> dict:
    """Convenience one-shot scoring (creates a rules scorer unless LLM requested)."""
    if scorer is None:
        scorer = FeatureScorer(config=config)
    return scorer.score(issue_data)


def score_issues_batch(issues: List[dict], scorer: Optional[FeatureScorer] = None, config: Optional[dict] = None, workers: int = 5) -> Dict[str, dict]:
    """Score a batch of issues concurrently. Returns {issue_key: detail}."""
    if scorer is None:
        scorer = FeatureScorer(config=config)
    results: Dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {pool.submit(scorer.score, i): i.get('key') for i in issues}
        for fut in as_completed(future_map):
            key = future_map[fut]
            try:
                results[key] = fut.result()
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Scoring failed for {key}: {e}")
    return results


def resolve_feature_config(db) -> Optional[dict]:
    """Read feature_complexity config variables from the config matrix (first rule found)."""
    try:
        import models
        metric = (
            db.query(models.KPIRuleMetric)
            .filter(models.KPIRuleMetric.metric_key.in_(("feature_complexity", "complexity_sp")))
            .first()
        )
        if metric and metric.variables:
            vars_ = metric.variables
            cfg = {
                "max_c": vars_.get("max_c", 5),
                "max_i": vars_.get("max_i", 5),
                "max_s": vars_.get("max_s", 5),
                "max_r": vars_.get("max_r", 3),
                "max_o": vars_.get("max_o", 2),
            }
            pm = vars_.get("point_map") or vars_.get("kpi_points_map")
            if pm:
                cfg["point_map"] = pm
            return cfg
    except Exception as e:  # noqa: BLE001
        logger.warning(f"resolve_feature_config failed: {e}")
    return None


def stored_feature_weight(issue_obj) -> float:
    """Read the persisted complexity_score, falling back to the rules scorer."""
    try:
        score = getattr(issue_obj, "complexity_score", None)
        if score is not None:
            return float(score)
    except Exception:  # noqa: BLE001
        pass
    raw = getattr(issue_obj, "raw_data", None) or {}
    return calculate_feature_weight(raw)


def stored_feature_detail(issue_obj) -> dict:
    """Return the display breakdown for an issue, preferring the persisted detail.

    Keys match the old analyze_multi_factor output: kpi_points, complexity,
    impact, scope, risk, ownership.
    """
    detail = getattr(issue_obj, "complexity_detail", None)
    score = getattr(issue_obj, "complexity_score", None)
    if isinstance(detail, dict) and detail:
        def _num(key, default):
            try:
                v = detail.get(key)
                return float(v) if v is not None else default
            except (TypeError, ValueError):
                return default
        return {
            "kpi_points": _num("kpi_points", float(score or 1.0)),
            "complexity": _num("technical_complexity", 0),
            "impact": _num("business_impact", 0),
            "scope": _num("system_scope", 0),
            "risk": _num("delivery_risk", 0),
            "ownership": _num("ownership_level", 0),
            "total_score": _num("total_score", 0),
            "score_type": detail.get("score_type", "stored"),
        }
    raw = getattr(issue_obj, "raw_data", None) or {}
    res = analyze_multi_factor(raw)
    res["kpi_points"] = float(score) if score is not None else res["kpi_points"]
    return res
