"""Credential-safe readiness report. Add --live for MySQL/provider probes."""
import argparse
import asyncio
import importlib.util
import io
import json
import shutil
import wave
from pathlib import Path
import httpx


def offline_checks():
    from ilma_api import settings
    from ilma_api.voice_assets import load_approved, ROOT
    checks = {
        'mysql_runtime': settings.DATABASE_URL.get_backend_name() == 'mysql',
        'rapidfuzz_installed': importlib.util.find_spec('rapidfuzz') is not None,
        'ffmpeg_available': bool(shutil.which(settings.FFMPEG_BINARY) or importlib.util.find_spec('imageio_ffmpeg')),
        'meta_configured': bool(settings.META_MODEL_API_KEY and settings.MUSE_VOICE_API_URL and settings.MUSE_VOICE_MODEL),
        'standard_models': all('contributor' not in name.lower() for name in [settings.MUSE_VOICE_MODEL, settings.MUSE_SPARK_MODEL]),
        'speech_configured': bool(settings.ELEVENLABS_API_KEY and settings.ELEVENLABS_VOICE_ID),
        'private_env_permissions': (ROOT / '.env').exists() and (ROOT / '.env').stat().st_mode & 0o777 == 0o600,
    }
    try: load_approved(ROOT / 'static/audio/fixed'); checks['reviewed_offline_clips'] = True
    except (OSError, ValueError, KeyError): checks['reviewed_offline_clips'] = False
    return checks


async def live_checks():
    from sqlalchemy import inspect
    from ilma_api.db import engine, SessionLocal
    from ilma_api.main import get_institution_index
    from ilma_api import settings
    result = {}
    try:
        tables = set(inspect(engine).get_table_names())
        result['mysql_connected'] = True
        result['voice_tables_ready'] = {'app_question_log','app_rate_counter','app_content'} <= tables
        with SessionLocal() as db: banks = get_institution_index(db)
        from ilma_api.replay_voice import resolve_expected
        missing = []
        for label in ['EBL','BRAC','City','MTB','NCC','Prime','DBBL','Bank Asia','SBAC']:
            try: resolve_expected(label, banks)
            except ValueError: missing.append(label)
        result['demo_banks_missing'] = missing
    except Exception:
        result['mysql_connected'] = False
    try:
        from ilma_api.voice import transcribe, VoiceError
        output = io.BytesIO()
        with wave.open(output, 'wb') as clip:
            clip.setnchannels(1); clip.setsampwidth(2); clip.setframerate(24000); clip.writeframes(b'\0\0' * 2400)
        try:
            await transcribe(output.getvalue(), 'bn', [])
            result['meta_authenticated'] = True
        except VoiceError as error:
            result['meta_authenticated'] = error.code == 'no_speech'
            if not result['meta_authenticated']: result['meta_error'] = error.code
    except Exception: result['meta_authenticated'] = False
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=False) as client:
            response = await client.get('https://api.elevenlabs.io/v1/voices/' + settings.ELEVENLABS_VOICE_ID,
                headers={'xi-api-key': settings.ELEVENLABS_API_KEY})
        result['speech_voice_accessible'] = response.status_code == 200
    except httpx.HTTPError: result['speech_voice_accessible'] = False
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    try:
        report = {'local': offline_checks()}
        print(json.dumps(report, indent=2), flush=True)
        if args.live:
            report['live'] = asyncio.run(live_checks()); print(json.dumps({'live':report['live']}, indent=2), flush=True)
        complete = all(report['local'].values()) and (not args.live or (report['live'].get('mysql_connected') and report['live'].get('voice_tables_ready') and report['live'].get('meta_authenticated') and report['live'].get('speech_voice_accessible') and not report['live'].get('demo_banks_missing')))
        raise SystemExit(0 if complete else 1)
    except (ValueError, OSError):
        raise SystemExit('Readiness check failed. Check private configuration; no secrets printed.') from None
