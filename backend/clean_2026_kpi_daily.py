from database import SessionLocal
from models import KPIEmployeeDaily
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_kpi_daily():
    db = SessionLocal()
    try:
        deleted = db.query(KPIEmployeeDaily).filter(KPIEmployeeDaily.date >= '2026-01-01').delete(synchronize_session=False)
        db.commit()
        logger.info(f"Deleted {deleted} rows from KPIEmployeeDaily for year >= 2026")
    except Exception as e:
        db.rollback()
        logger.error(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    clean_kpi_daily()
