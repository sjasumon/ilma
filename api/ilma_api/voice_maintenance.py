"""Daily MySQL retention cleanup. Run with python -m ilma_api.voice_maintenance."""
from datetime import datetime, timedelta
from sqlalchemy import delete
from ilma_api.db import SessionLocal, AppQuestionLog, AppRateCounter


def cleanup(db, now=None):
    now = now or datetime.utcnow()
    logs = db.execute(delete(AppQuestionLog).where(AppQuestionLog.created_at < now - timedelta(days=30))).rowcount
    counters = db.execute(delete(AppRateCounter).where(AppRateCounter.expires_at < now)).rowcount
    db.commit()
    return logs, counters


if __name__ == '__main__':
    try:
        with SessionLocal() as db:
            logs, counters = cleanup(db)
        print(f'Retention cleanup: {logs} old log rows, {counters} expired counters removed.')
    except Exception:
        raise SystemExit('MySQL cleanup failed. Check database configuration/access; no credentials were printed.') from None
