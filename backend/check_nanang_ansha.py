import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
import models
from datetime import date
from sqlalchemy import func
import json

db = SessionLocal()

nanang = db.query(models.User).filter(models.User.full_name.ilike('%nanang%')).first()
ansha = db.query(models.User).filter(models.User.full_name.ilike('%ansha%')).first()

def get_kpi(user):
    if not user:
        return None
        
    records = db.query(models.KPIEmployeeDaily).filter(
        models.KPIEmployeeDaily.user_id == user.id,
        models.KPIEmployeeDaily.date >= date(2026, 1, 1),
        models.KPIEmployeeDaily.date <= date(2026, 12, 31)
    ).all()
    
    overall = sum(r.overall_score for r in records if r.overall_score)
    
    agg = {}
    for r in records:
        details = r.kpi_breakdown
        if not details: continue
        if isinstance(details, str):
            details = json.loads(details)
            
        for d in details:
            k = d.get('metric_name', 'unknown')
            if k not in agg:
                agg[k] = {'raw': 0.0, 'capped': 0.0, 'weighted': 0.0, 'weight': d.get('weight', 0)}
            
            raw = float(d.get('raw_score') or 0.0)
            capped = float(d.get('capped_score') or d.get('calculated_score') or 0.0)
            weighted = float(d.get('weighted_score') or 0.0)
            
            agg[k]['raw'] += raw
            agg[k]['capped'] += capped
            agg[k]['weighted'] += weighted
            
    days = len(records)
    avg_overall = overall / days if days > 0 else 0
    
    return {
        'name': user.full_name,
        'days': days,
        'overall_sum': overall,
        'avg_overall': avg_overall,
        'metrics': agg
    }

n_data = get_kpi(nanang)
a_data = get_kpi(ansha)

print("=== NANANG ===")
if n_data:
    print(f"Days: {n_data['days']}, Avg Overall: {n_data['avg_overall']:.2f}")
    for k, v in n_data['metrics'].items():
        avg_capped = v['capped'] / n_data['days'] if n_data['days'] else 0
        avg_weighted = v['weighted'] / n_data['days'] if n_data['days'] else 0
        print(f"  {k}: sum_raw={v['raw']:.2f}, avg_capped={avg_capped:.2f}, avg_weighted={avg_weighted:.2f}, weight={v['weight']}%")

print("\n=== ANSHA ===")
if a_data:
    print(f"Days: {a_data['days']}, Avg Overall: {a_data['avg_overall']:.2f}")
    for k, v in a_data['metrics'].items():
        avg_capped = v['capped'] / a_data['days'] if a_data['days'] else 0
        avg_weighted = v['weighted'] / a_data['days'] if a_data['days'] else 0
        print(f"  {k}: sum_raw={v['raw']:.2f}, avg_capped={avg_capped:.2f}, avg_weighted={avg_weighted:.2f}, weight={v['weight']}%")
