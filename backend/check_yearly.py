import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
import models
from yearly_kpi_engine import YearlyKPIEngine

db = SessionLocal()
nanang = db.query(models.User).filter(models.User.full_name.ilike('%nanang%')).first()
ansha = db.query(models.User).filter(models.User.full_name.ilike('%ansha%')).first()

print('Calculating Yearly for Nanang...')
n_res = YearlyKPIEngine.calculate_yearly_kpi(db, nanang, 2026)
print(f"Nanang Final KPI: {n_res.get('final_kpi_score', 0)}")
print('Details:')
for m in n_res.get('metrics_breakdown', []):
    print(f"  {m['metric_name']}: weight={m['weight']}% capped={m['capped_score']} weighted={m['weighted_score']}")

print('\nCalculating Yearly for Ansha...')
a_res = YearlyKPIEngine.calculate_yearly_kpi(db, ansha, 2026)
print(f"Ansha Final KPI: {a_res.get('final_kpi_score', 0)}")
print('Details:')
for m in a_res.get('metrics_breakdown', []):
    print(f"  {m['metric_name']}: weight={m['weight']}% capped={m['capped_score']} weighted={m['weighted_score']}")
