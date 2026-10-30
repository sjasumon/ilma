"""Generate hash-checked, owner-approved loan examples without rewriting text."""
import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'api'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_approved_card_clips import generate
from ilma_api.loan_catalog import DEFAULTS
from ilma_api.loan_readout import CLIP_KEYS


def plan(path, bindings):
    data = json.loads(Path(path).read_text())
    snapshots = json.loads(Path(bindings).read_text())
    clips = data['clips']
    if len(clips) != 4 or sum(len(c['text']) for c in clips) != data['total_chars']:
        raise ValueError('Approved loan count/characters mismatch')
    kinds = {key: kind for kind, key in CLIP_KEYS.items()}
    items = []
    for clip in clips:
        key, text = clip['key'], clip['text']
        if key not in kinds:
            raise ValueError('Unknown approved loan key')
        kind = kinds[key]
        file = 'static/audio/services/bn/loan_' + key.removeprefix('loan:bn:') + '.mp3'
        if clip['file'] != file:
            raise ValueError('Approved loan filename changed')
        digest = hashlib.sha256(text.encode()).hexdigest()
        if len(text) != clip['chars'] or digest != clip['text_sha256']:
            raise ValueError('Approved loan text changed')
        snapshot = snapshots[kind]
        readout = snapshot['readout']
        amount, years = DEFAULTS[kind]
        if (readout['example_amount'], readout['example_years']) != (amount, years):
            raise ValueError('Loan default example changed')
        source = readout['source_sha256']
        if not re.fullmatch(r'[a-f0-9]{64}', source) or not snapshot['rows'] or any(r['stale'] for r in snapshot['rows']):
            raise ValueError('Missing current loan source binding')
        items.append(dict(key=key, loan_type=kind, text=text, file=file,
                          text_sha256=digest, source_sha256=source,
                          example_amount=amount, example_years=years,
                          approved_exact_text=True))
    if len({i['key'] for i in items}) != 4:
        raise ValueError('Missing or duplicate loan clip')
    return items


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--approved-json', type=Path, required=True)
    p.add_argument('--bindings', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--env-file', type=Path)
    p.add_argument('--request-timeout', type=int, help='Explicitly approved offline override; otherwise use the package deadline')
    p.add_argument('--generate', action='store_true')
    args = p.parse_args()
    items = plan(args.approved_json, args.bindings)
    print('TOTAL:', len(items), 'clips;', sum(len(i['text']) for i in items), 'characters', flush=True)
    if args.generate:
        from dotenv import load_dotenv
        if args.env_file:
            load_dotenv(args.env_file, override=True)
        os.environ['DB_NAME'] = 'ilma'
        import importlib
        from ilma_api import settings
        importlib.reload(settings)
        import httpx
        from ilma_api.elevenlabs import SpeechFailure
        # Offline deadlines follow the supplied package; runtime limits are unchanged.
        data = json.loads(args.approved_json.read_text())
        timeout = args.request_timeout if args.request_timeout is not None else data['elevenlabs']['fallback_rules']['try_next_key_on_timeout_seconds']
        if not isinstance(timeout, int) or not 1 <= timeout <= 120:
            raise ValueError('Invalid approved request timeout')
        async def run():
            async with httpx.AsyncClient(follow_redirects=False) as client:
                await generate(items, args.output, client, request_timeout=timeout)
        try:
            asyncio.run(run())
        except (ValueError, SpeechFailure) as error:
            print(str(error), file=sys.stderr)
            sys.exit(1)
