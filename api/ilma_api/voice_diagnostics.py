"""Explicit development-only capture. No public diagnostics/download endpoint."""
import argparse
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from ilma_api import settings
from ilma_api.db import VoiceDiagnostic


def enabled():
    return settings.ILMA_ENV == 'development' and settings.VOICE_DIAGNOSTICS_ENABLED


def start_capture(audio, mime, language):
    if not enabled(): return None
    return dict(diagnostic_id=uuid.uuid4().hex, audio=audio, mime=mime,
                language=language, meta_transcript=None, events=[])


def capture_event(capture, chunk):
    # Never retain synthesized audio/base64. Store only diagnostic stages.
    if len(capture['events']) >= 20: return
    lines = chunk.splitlines()
    name = next((line[7:] for line in lines if line.startswith('event: ')), '')
    if name not in {'transcript', 'match', 'result', 'error'}: return
    payload = next((line[6:] for line in lines if line.startswith('data: ')), '{}')
    capture['events'].append({'event': name, 'data': json.loads(payload)})


def prune(db):
    db.execute(delete(VoiceDiagnostic).where(VoiceDiagnostic.created_at < datetime.utcnow() - timedelta(days=7)))
    # Keep at most 200 samples, even during intensive testing.
    excess = list(db.scalars(select(VoiceDiagnostic.diagnostic_id).order_by(
        VoiceDiagnostic.created_at.desc(), VoiceDiagnostic.diagnostic_id.desc()).offset(200)))
    if excess: db.execute(delete(VoiceDiagnostic).where(VoiceDiagnostic.diagnostic_id.in_(excess)))


def save_capture(capture, bind):
    if not enabled(): return
    try:
        with Session(bind) as db:
            db.add(VoiceDiagnostic(**capture))
            db.flush()
            prune(db)
            db.commit()
    except Exception:
        # Diagnostics must not turn a successful voice request into a failure.
        logging.getLogger(__name__).warning('voice_diagnostic_save_failed; run development diagnostics setup')
    finally:
        capture.clear()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['setup', 'list', 'export', 'label', 'prune'])
    parser.add_argument('--id')
    parser.add_argument('--expected')
    parser.add_argument('--directory', default='voice-diagnostics')
    args = parser.parse_args()
    if not enabled(): parser.error('Requires ILMA_ENV=development and VOICE_DIAGNOSTICS_ENABLED=true. Never enable on production.')
    from ilma_api.db import engine
    if args.action == 'setup':
        VoiceDiagnostic.__table__.create(engine, checkfirst=True)
        print('Development diagnostic table ready; raw audio and transcripts will be stored in MySQL.')
        return
    with Session(engine) as db:
        prune(db)
        if args.action == 'list':
            for row in db.scalars(select(VoiceDiagnostic).order_by(VoiceDiagnostic.created_at.desc())):
                print(row.diagnostic_id, row.created_at.isoformat(), row.language,
                      ','.join(e['data'].get('code', e['event']) for e in row.events))
        elif args.action in {'export', 'label'}:
            row = db.get(VoiceDiagnostic, args.id)
            if not row: parser.error('Diagnostic ID not found (samples expire after seven days).')
            if args.action == 'label':
                if not args.expected or len(args.expected) > 5000: parser.error('Provide --expected (up to 5000 characters).')
                row.expected_question = args.expected
            else:
                directory = Path(args.directory).resolve()
                public = Path(__file__).resolve().parents[2] / 'static'
                if directory == public or public in directory.parents: parser.error('Export outside static/; diagnostic audio is private.')
                directory.mkdir(parents=True, exist_ok=True, mode=0o700)
                suffix = {'audio/webm': '.webm', 'audio/mp4': '.mp4', 'audio/wav': '.wav', 'audio/x-wav': '.wav'}[row.mime]
                for filename, content in [(row.diagnostic_id + suffix, row.audio), (row.diagnostic_id + '.json',
                    json.dumps({'id': row.diagnostic_id, 'language': row.language,
                        'meta_transcript': row.meta_transcript, 'expected_question': row.expected_question,
                        'events': row.events}, ensure_ascii=False, indent=2).encode())]:
                    path = directory / filename
                    with path.open('xb') as output: output.write(content)
                    path.chmod(0o600)
                print('Exported paired audio and JSON to the private directory.')
        db.commit()


if __name__ == '__main__': main()
