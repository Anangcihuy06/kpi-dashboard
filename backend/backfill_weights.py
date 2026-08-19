import json
import sys
from database import SessionLocal
import models
from feature_analyzer import FeatureScorer, resolve_feature_config, score_issues_batch

"""
Backfill persisted feature complexity scores for existing Jira issues.

Usage:
  python backfill_weights.py            # rules scorer, only fills missing scores
  python backfill_weights.py --force    # re-score everything
  python backfill_weights.py --llm      # use Z.AI LLM scorer
"""
FORCE = "--force" in sys.argv
USE_LLM = "--llm" in sys.argv

db = SessionLocal()
cfg = resolve_feature_config(db)
scorer = FeatureScorer(config=cfg, use_llm=USE_LLM)

issues = db.query(models.RawJiraIssue).all()
if not FORCE:
    issues = [i for i in issues if i.complexity_score is None]

print(f"Backfilling complexity scores for {len(issues)} issues (mode={scorer.mode}, force={FORCE})")

raw_data_list = []
for ji in issues:
    raw = dict(ji.raw_data or {})
    raw.setdefault('key', ji.issue_key)
    raw_data_list.append((ji, raw))
scores = score_issues_batch([r for _, r in raw_data_list], scorer, config=cfg, workers=5)

updated = 0
for ji, raw in raw_data_list:
    res = scores.get(ji.issue_key)
    if not res:
        continue
    ji.complexity_score = float(res["kpi_points"])
    ji.complexity_detail = {
        "technical_complexity": res["technical_complexity"],
        "business_impact": res["business_impact"],
        "system_scope": res["system_scope"],
        "delivery_risk": res["delivery_risk"],
        "ownership_level": res["ownership_level"],
        "total_score": res["total_score"],
        "kpi_points": float(res["kpi_points"]),
        "score_type": res.get("score_type", "rules"),
        "model": res.get("model"),
        "prompt_version": res.get("prompt_version"),
    }
    updated += 1

db.commit()

# Refresh precomputed aggregates
try:
    from precompute_metrics import compute_all_year_metrics
    years = set()
    for ji in issues:
        if ji.resolved_date:
            years.add(ji.resolved_date.year)
        elif ji.updated_date:
            years.add(ji.updated_date.year)
    for y in years:
        compute_all_year_metrics(db, y, force=True)
except Exception as e:
    print(f"Precompute refresh skipped: {e}")

db.close()
print(f"Updated {updated} issues with persisted complexity scores.")
