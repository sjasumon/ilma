from datetime import datetime, timedelta
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from ilma_api import settings
from ilma_api.db import Base, VoiceDiagnostic, AppQuestionLog, AppRateCounter
from ilma_api.voice_maintenance import cleanup


def test_idle_diagnostics_expire_even_after_capture_disabled():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    now = datetime(2026, 10, 27)
    with Session(engine) as db:
        for name, age in [('old', 8), ('recent', 1)]:
            db.add(VoiceDiagnostic(diagnostic_id=name, created_at=now - timedelta(days=age),
                audio=b'audio', mime='audio/webm', language='bn', events=[]))
        db.add(AppRateCounter(key='expired', count=1, expires_at=now-timedelta(days=1)))
        db.commit()
        with patch.object(settings, 'VOICE_DIAGNOSTICS_ENABLED', False):
            assert cleanup(db, now) == (0, 1)
        assert list(db.scalars(select(VoiceDiagnostic.diagnostic_id))) == ['recent']
    engine.dispose()
