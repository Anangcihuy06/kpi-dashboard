from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
    tables = result.fetchall()
    print('Current database tables:')
    for table in sorted([t[0] for t in tables]):
        print(f'  - {table}')