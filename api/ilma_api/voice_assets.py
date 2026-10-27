"""Generate, review and publish fixed voice clips. Never marks native review itself."""
import argparse
import asyncio
import base64
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = {
    'welcome': ('হ্যালো, আমি ইলমা। আপনার সঞ্চয়ের বিশ্বস্ত সাথী।', 'Hello, I am Ilma, your trusted savings companion.'),
    'hint': ('ব্যাংকের নাম বলুন বা প্রশ্ন করুন।', 'Say a bank name or ask a question.'),
    'strong': ('ভালো অবস্থা', 'Strong'), 'watch': ('সতর্ক থাকুন', 'Watch'),
    'high': ('ঝুঁকি বেশি', 'High risk'), 'no_data': ('তথ্য কম', 'Not enough data'),
    'E-01': ('ইন্টারনেট সংযোগ নেই। সংযোগ ফিরলে আবার চেষ্টা করুন।', 'You are offline. Reconnect and try again.'),
    'E-03': ('মাইক্রোফোনের অনুমতি দিন, অথবা লিখে খুঁজুন।', 'Allow microphone access, or type to search.'),
    'E-04': ('বুঝতে পারিনি। আবার বলুন বা লিখুন।', 'Not understood. Please speak again or type.'),
    'privacy': ('পিন, ওটিপি বা অ্যাকাউন্ট নম্বর কখনো বলবেন না।', 'Never say your PIN, OTP or account number.'),
    'insurance': (None, None),
}


def digest(data): return hashlib.sha256(data).hexdigest()


def validate_review(item):
    return bool(item.get('reviewer') and item.get('reviewed_at') and item.get('reviewed') is True and
                item.get('text_sha256') == digest(item.get('text', '').encode()))


def load_approved(directory):
    directory = Path(directory)
    manifest = json.loads((directory / 'manifest.json').read_text())
    required = {f'{lang}:{key}' for lang in ('bn', 'en') for key in CATALOG}
    if set(manifest.get('clips', {})) != required: raise ValueError('Incomplete fixed clip bundle.')
    for key, item in manifest['clips'].items():
        if not validate_review(item): raise ValueError('Native review is missing or text changed.')
        name = item.get('file', '')
        if not re.fullmatch(r'[a-zA-Z0-9_-]+\.(?:opus|mp3)', name): raise ValueError('Invalid clip name.')
        if digest((directory / name).read_bytes()) != item['audio_sha256']: raise ValueError('Clip changed after review.')
        fallback = item.get('fallback_file', '')
        if not re.fullmatch(r'[a-zA-Z0-9_-]+\.mp3', fallback): raise ValueError('MP3 fallback is missing.')
        if digest((directory / fallback).read_bytes()) != item.get('fallback_sha256'): raise ValueError('Fallback changed.')
    if sum((directory / item[field]).stat().st_size for item in manifest['clips'].values() for field in ('file', 'fallback_file')) > 2 * 1024 * 1024: raise ValueError('Offline audio bundle exceeds 2 MiB.')
    return manifest


async def normalize_fixed(audio, kind):
    from ilma_api.voice import ffmpeg_executable
    codec = ['-c:a', 'libopus', '-b:a', '32k', '-f', 'opus'] if kind == 'opus' else ['-c:a', 'libmp3lame', '-b:a', '64k', '-f', 'mp3']
    filters = 'silenceremove=start_periods=1:start_silence=0.15:start_duration=0.15:start_threshold=-50dB,areverse,silenceremove=start_periods=1:start_silence=0.15:start_duration=0.15:start_threshold=-50dB,areverse,loudnorm=I=-16:TP=-1:LRA=11'
    process = await asyncio.create_subprocess_exec(ffmpeg_executable(), '-hide_banner', '-loglevel', 'error', '-nostdin', '-protocol_whitelist', 'pipe', '-i', 'pipe:0', '-map_metadata', '-1', '-ac', '1', '-ar', '48000', '-af', filters, *codec, 'pipe:1', stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    try: output, _ = await asyncio.wait_for(process.communicate(audio), 20)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        process.kill(); await process.wait(); raise
    if process.returncode or not output: raise ValueError('Fixed audio normalization failed.')
    return output


async def generate(directory, limit=None):
    from ilma_api.voice_pipeline import speech
    from ilma_api.voice import ffmpeg_executable
    ffmpeg_executable()  # fail before spending provider credits if conversion is unavailable
    from ilma_api.db import SessionLocal, InsuranceRule
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    clips, failures = {}, []
    for language, index in [('bn', 0), ('en', 1)]:
        for key, text in CATALOG.items():
            if limit is not None and len(clips) + len(failures) >= limit: break
            phrase = text[index]
            if key == 'insurance':
                try:
                    with SessionLocal() as db:
                        row = db.query(InsuranceRule).filter_by(inst_type='bank').first()
                        phrase = (row.text_bn if language == 'bn' else row.text_en) if row and row.source else None
                except Exception: phrase = None
            if not phrase:
                failures.append(language + ':' + key); continue
            url = await speech(phrase, language)
            if not url:
                failures.append(language + ':' + key); continue
            audio = base64.b64decode(url.partition(',')[2])
            try:
                opus = await normalize_fixed(audio, 'opus')
                mp3 = await normalize_fixed(audio, 'mp3')
            except Exception:
                failures.append(language + ':' + key); continue
            filename = language + '-' + key + '.opus'
            fallback = language + '-' + key + '.mp3'
            (directory / filename).write_bytes(opus)
            (directory / fallback).write_bytes(mp3)
            clips[language + ':' + key] = {'file': filename, 'fallback_file': fallback, 'text': phrase, 'text_sha256': digest(phrase.encode()),
                'audio_sha256': digest(opus), 'fallback_sha256': digest(mp3), 'reviewed': False, 'reviewer': '', 'reviewed_at': ''}
    manifest = {'version': 1, 'clips': clips, 'failed': failures}
    (directory / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f'Generated {len(clips)} draft clips; {len(failures)} unavailable. Native review is required before publishing.')
    return not failures and len(clips) == len(CATALOG) * 2


def review(directory, reviewer, keys):
    if not reviewer.strip(): raise ValueError('Reviewer name is required.')
    path = Path(directory) / 'manifest.json'
    manifest = json.loads(path.read_text())
    for key in keys:
        item = manifest['clips'][key]
        if digest((path.parent / item['file']).read_bytes()) != item['audio_sha256']: raise ValueError('Audio changed.')
        if digest(item['text'].encode()) != item['text_sha256']: raise ValueError('Text changed; regenerate the clip before review.')
        item.update(reviewed=True, reviewer=reviewer, reviewed_at=datetime.now(timezone.utc).isoformat(), text_sha256=digest(item['text'].encode()))
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))


def publish(directory):
    manifest = load_approved(directory)
    target = ROOT / 'static/audio/fixed'; target.mkdir(parents=True, exist_ok=True)
    # Bundle copying only, no user recordings. Review metadata remains auditable.
    for item in manifest['clips'].values():
        for field in ('file', 'fallback_file'): shutil.copyfile(Path(directory) / item[field], target / item[field])
    (target / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"Published {len(manifest['clips'])} reviewed fixed clips.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['generate', 'review', 'publish'])
    parser.add_argument('--directory', default='voice-drafts')
    parser.add_argument('--reviewer')
    parser.add_argument('--keys', nargs='*', default=[])
    parser.add_argument('--limit', type=int)
    parser.add_argument('--all', action='store_true', help='Explicitly confirm you reviewed every generated clip')
    args = parser.parse_args()
    try:
        if args.action == 'generate': raise SystemExit(0 if asyncio.run(generate(args.directory, args.limit)) else 1)
        if args.action == 'review':
            keys = list(json.loads((Path(args.directory) / 'manifest.json').read_text())['clips']) if args.all else args.keys
            if not keys: raise ValueError('Select clips to review.')
            review(args.directory, args.reviewer or '', keys)
        if args.action == 'publish': publish(args.directory)
    except Exception:
        raise SystemExit('Fixed clip operation failed. Check generated files and native review metadata; no secrets printed.') from None
