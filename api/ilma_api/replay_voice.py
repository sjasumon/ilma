"""Replay APP_SPEC_02 audio manifests against the actual HTTP/SSE voice endpoint."""
import argparse
import asyncio
import csv
import json
import mimetypes
import statistics
import time
from pathlib import Path
import httpx

TARGETS = {'clean_bn': .98, 'fan_bn': .95, 'english': .98, 'real': .90}


def read_manifest(path, audio_dir, columns=None, default_language="bn"):
    columns = columns or {}
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    if not rows: raise ValueError('Manifest is empty.')
    normalized = []
    for number, row in enumerate(rows, 1):
        file = row.get(columns['file']) if columns.get('file') else next((row.get(key) for key in ('file', 'filename', 'audio_file', 'audio_path', 'file_path', 'path') if row.get(key)), None)
        expected = row.get(columns['bank'], '') if columns.get('bank') else next((row.get(key) for key in ('institution_id', 'bank_id', 'bank', 'expected_bank', 'bank_name') if row.get(key)), '')
        language = (row.get(columns['language']) if columns.get('language') else row.get('language') or row.get('lang')) or default_language
        language = {'bengali':'bn','bangla':'bn','bn-bd':'bn','english':'en','en-us':'en','en-gb':'en'}.get(language.lower(), language.lower())
        path = Path(audio_dir) / file if file else None
        if path is not None and not path.is_file(): path = Path(audio_dir) / str(file).replace('\\', '/').split('/')[-1]
        if path is None or not path.is_file(): raise ValueError(f'Audio missing at row {number}.')
        if language not in {'bn', 'en'}: raise ValueError(f'Invalid language at row {number}.')
        normalized.append({**row, 'path': path, 'bank': expected, 'language': language, 'ui_lang': row.get('ui_lang') or language})
    return normalized


def resolve_expected(value, bank_index):
    from ilma_api.voice_text import normalize_alias
    if not value or value.lower() in {'none', 'null', 'no_bank'}: return None
    if value.isdigit(): return int(value)
    key = normalize_alias(value)
    found = {bank['id'] for bank in bank_index if key in {normalize_alias(name) for name in [bank['slug'], bank['name_bn'], bank['name_en'], *bank.get('aliases', [])]}}
    if len(found) != 1: raise ValueError('Expected bank label is missing or ambiguous in the verified bank index.')
    return next(iter(found))


def public_transcript(text):
    # Diagnostic reports retain bank words, not numbers/PINs/amounts from real voices.
    from ilma_api.voice_numbers import normalize_numbers, NUMBERS
    import re
    text = normalize_numbers(text)
    text = re.sub(r'[0-9০-৯][0-9০-৯,./-]*', '[number]', text)
    return ' '.join('[number]' if word.strip('.,?!।').lower() in NUMBERS else word for word in text.split())


async def replay_one(client, row, expected, speak=False):
    started, transcript_ms, result_ms = time.monotonic(), None, None
    transcript, language, matched, error = '', '', [], None
    audio = row['path'].read_bytes()
    if len(audio) > 1024 * 1024: raise ValueError('Replay clip exceeds the app upload cap.')
    mime = mimetypes.guess_type(row['path'].name)[0] or 'audio/webm'
    if row['path'].suffix.lower() in {'.wav', '.wave'}: mime = 'audio/wav'
    if row['path'].suffix.lower() in {'.mp4', '.m4a'}: mime = 'audio/mp4'
    async with client.stream('POST', '/v1/voice', files={
        'audio': (row['path'].name, audio, mime),
        'context': (None, json.dumps({'tab': row.get('tab') or 'home', 'ui_lang': row.get('ui_lang') or 'bn', 'speak': speak}))
    }) as response:
        if response.status_code != 200:
            return {'bank_expected': expected is not None, 'bank_ok': False, 'language_ok': False, 'error': 'http_' + str(response.status_code)}
        event = ''
        async for line in response.aiter_lines():
            if line.startswith('event: '): event = line[7:]
            if not line.startswith('data: '): continue
            payload = json.loads(line[6:])
            if event == 'transcript':
                transcript, language = payload['text'], payload['language']
                transcript_ms = int((time.monotonic() - started) * 1000)
            elif event == 'match': matched = payload.get('institution_ids', [])
            elif event == 'result': result_ms = int((time.monotonic() - started) * 1000)
            elif event == 'error': error = payload.get('code', 'unknown')
    return {'bank_expected': expected is not None, 'transcript': public_transcript(transcript), 'matched_ids': matched, 'language': language,
            'bank_ok': (expected in matched) if expected is not None else not matched,
            'language_ok': language == row['language'], 'transcript_ms': transcript_ms,
            'result_ms': result_ms, 'total_ms': int((time.monotonic() - started) * 1000), 'error': error}


def summarize(results, suite, rows):
    eligible = [row for row in results if row.get('bank_expected', True)]
    bank = sum(bool(row.get('bank_ok')) for row in eligible) / len(eligible) if eligible else 0
    language = sum(bool(row.get('language_ok')) for row in results) / len(results)
    latency = [row['result_ms'] for row in results if row.get('result_ms') is not None]
    median = statistics.median(latency) if latency else None
    quiet = [result for result, row in zip(results, rows) if row.get('condition') == 'quiet' and result.get('bank_expected', True)]
    quiet_accuracy = sum(bool(row.get('bank_ok')) for row in quiet) / len(quiet) if quiet else None
    rate = language if suite == 'english' else (quiet_accuracy or 0) if suite == 'real' else bank
    coverage = suite != 'real' or (len(rows) >= 20 and {'builder', 'woman', 'over60'} <= {row.get('speaker_role') for row in rows} and {'quiet', 'noisy'} <= {row.get('condition') for row in rows} and len({row.get('bank') for row in rows if row.get('test_kind') == 'bank'}) >= 9 and sum(row.get('test_kind') == 'question' for row in rows) >= 5)
    return {'suite': suite, 'count': len(results), 'bank_accuracy': bank, 'language_accuracy': language,
            'median_result_ms': median, 'coverage_complete': coverage, 'clean_real_bank_accuracy': quiet_accuracy if suite == 'real' else None, 'transport_errors': sum(bool(row.get('error')) for row in results),
            'passed': coverage and rate >= TARGETS[suite] and median is not None and median <= 4000,
            'requires_manual_review': suite == 'real' and quiet_accuracy is not None and quiet_accuracy < .9}


async def main(args):
    rows = read_manifest(args.manifest, args.audio_dir, {"file": args.file_column, "bank": args.bank_column, "language": args.language_column}, "en" if args.suite == "english" else "bn")
    async with httpx.AsyncClient(base_url=args.base_url.rstrip('/'), timeout=65, follow_redirects=False) as client:
        index = await client.get('/v1/institutions/index'); index.raise_for_status()
        banks = index.json()
        results = []
        for number, row in enumerate(rows, 1):
            result = await replay_one(client, row, resolve_expected(row['bank'], banks), args.speak)
            results.append(result)
            print(json.dumps({'row': number, **result}, ensure_ascii=False), flush=True)
    summary = summarize(results, args.suite, rows)
    print(json.dumps(summary, indent=2), flush=True)
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(json.dumps({'summary': summary, 'results': results}, ensure_ascii=False, indent=2))
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--audio-dir', required=True)
    parser.add_argument('--base-url', default='http://127.0.0.1:8001')
    parser.add_argument('--suite', choices=TARGETS, required=True)
    parser.add_argument('--report')
    parser.add_argument('--file-column')
    parser.add_argument('--bank-column')
    parser.add_argument('--language-column')
    parser.add_argument('--speak', action='store_true')
    try: raise SystemExit(asyncio.run(main(parser.parse_args())))
    except (httpx.HTTPError, ValueError, OSError):
        raise SystemExit('Replay could not run. Check the manifest, audio paths and server connection; no credentials printed.') from None
