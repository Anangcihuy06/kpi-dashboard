# Production Database Setup Guide

## Database Setup for Railway Deployment

### Problem
The Railway deployment is showing 500 Internal Server Error because the production database doesn't have the required initial data (divisions, integration settings).

### Solution

#### 1. Environment Variables (Required for Railway)
Set these environment variables in your Railway project:

```bash
# Database URL (Railway will provide this automatically if using Railway Postgres)
# DATABASE_URL=postgresql://user:pass@host:port/dbname

# Encryption key for tokens
ENCRYPTION_KEY=your-secure-encryption-key-here

# Optional: If you want to use SQLite instead
# DATABASE_URL=sqlite:///./database.db
```

#### 2. Database Initialization
The database will be auto-initialized on first startup through the `lifespan()` function in `main.py`, but you need to ensure:

1. **Database tables are created**: This happens automatically via `Base.metadata.create_all(bind=engine)`
2. **Default divisions exist**: These are created by the setup script
3. **Integration settings exist**: Default settings are created by setup script

#### 3. Run Setup Script (Manual)
If you need to manually set up the database, run:

```bash
cd backend
python setup_database.py
```

This script will:
- Create all required tables
- Add default divisions (IT, HR, Finance, Sales, Marketing)
- Create default integration settings
- Verify database health

#### 4. Verify Database Connection
Test if the database is working:

```bash
cd backend
python -c "
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) FROM divisions'))
    print(f'Divisions: {result.scalar()}')
"
```

#### 5. Railway-Specific Setup

If using Railway's PostgreSQL:

1. **Create Railway PostgreSQL service** 
2. **Get the DATABASE_URL** from Railway dashboard
3. **Add DATABASE_URL to your Railway app environment variables**
4. **Restart the Railway application**

The database schema will be created automatically on first startup.

#### 6. Common Issues & Solutions

**Issue**: 500 Internal Server Error
- **Cause**: Database tables or initial data missing
- **Solution**: Run setup_database.py or restart the app to trigger auto-migration

**Issue**: Database connection errors
- **Cause**: Wrong DATABASE_URL or database not accessible
- **Solution**: Verify DATABASE_URL format and network connectivity

**Issue**: Division lookup errors
- **Cause**: No divisions exist in database
- **Solution**: Ensure setup_database.py runs or manually add divisions

#### 7. Monitoring Database Health

```bash
# Check database tables
python -c "
from database import engine
from sqlalchemy import inspect

inspector = inspect(engine)
print('Tables:', inspector.get_table_names())
"

# Check data counts
python -c "
from database import SessionLocal
from models import Division, User

db = SessionLocal()
print(f'Users: {db.query(User).count()}')
print(f'Divisions: {db.query(Division).count()}')
db.close()
"
```

#### 8. Auto-Migration Details

The `lifespan()` function in `main.py` handles:
- Auto-creation of database tables
- Manual column additions for group_id/group_name
- Seeding initial data if database is empty
- Setting up default IT division if none exists

This runs automatically on app startup.

### Production Deployment Checklist

- [ ] DATABASE_URL environment variable set correctly
- [ ] ENCRYPTION_KEY environment variable set
- [ ] Railway PostgreSQL service created (if using PostgreSQL)
- [ ] App restarted after environment changes
- [ ] Database tables created successfully
- [ ] Default divisions exist (IT division at minimum)
- [ ] Integration settings exist
- [ ] Test login endpoint returns 401 (expected) instead of 500

### Testing Production Deployment

1. **Check basic endpoint**:
```bash
curl https://services-kpi-production.up.railway.app/api/v1/sync/status
```
Should return JSON response, not 500 error.

2. **Check divisions endpoint**:
```bash
curl https://services-kpi-production.up.railway.app/api/v1/divisions
```
Should return array of divisions.

3. **Test login with invalid credentials**:
```bash
curl -X POST https://services-kpi-production.up.railway.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}'
```
Should return 401 Unauthorized (not 500 error).

### Quick Fix for Production

If production is currently showing 500 errors, run this on the Railway server:

```bash
cd backend
python setup_database.py
# Then restart the app
```

Or set up a Railway health check that runs this setup script automatically on deployment.