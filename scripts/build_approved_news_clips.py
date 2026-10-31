"""Build reviewed news and regulatory announcement recordings verbatim from approved document."""
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


def load_plan(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    clips = data['clips']
    if len(clips) != 42 or sum(len(c['text']) for c in clips.values()) != data['total_chars']:
        raise ValueError('Approved news clip count or character total mismatch')
    items = []
    for key, clip in clips.items():
        text = clip['text']
        original = hashlib.sha256(text.encode('utf-8')).hexdigest()
        if len(text) != clip['chars'] or original != clip['text_sha256']:
            raise ValueError(f'Approved news text hash mismatch for {key}')
        file_path = clip['file']
        items.append(dict(
            key=key,
            item_id=clip['item_id'],
            lang=clip['lang'],
            category=clip['category'],
            file=file_path,
            text=text,
            text_sha256=original,
            approved_exact_text=True
        ))
    return items


async def generate(items, output_dir, client, request_timeout=120):
    from ilma_api import elevenlabs
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    manifest_path = output_path / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {'version': 1, 'clips': {}}

    for item in items:
        target = output_path / Path(item['file']).name if not item['file'].startswith('static/audio/news/') else Path(item['file'])
        old = manifest['clips'].get(item['key'], {})
        if target.is_file() and old.get('text_sha256') == item['text_sha256']:
            print(f"{item['key']} unchanged", flush=True)
            continue
        audio, used = await elevenlabs.synthesize(
            client,
            item['text'],
            voice_settings={'stability': 0.5, 'similarity_boost': 0.75},
            timeout_seconds=request_timeout
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(audio)
        manifest['clips'][item['key']] = {
            **item,
            **used,
            'audio_sha256': hashlib.sha256(audio).hexdigest(),
            'reviewed': True
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f"{item['key']} generated and saved", flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approved-json', type=Path, default=Path('docs/news_clips_approved.json'))
    parser.add_argument('--output', type=Path, default=Path('static/audio/news'))
    parser.add_argument('--generate', action='store_true')
    parser.add_argument('--env-file', type=Path)
    args = parser.parse_args()

    items = load_plan(args.approved_json)
    print(f"TOTAL: {len(items)} clips; {sum(len(i['text']) for i in items)} characters", flush=True)

    if args.generate:
        if args.env_file:
            from dotenv import load_dotenv
            load_dotenv(args.env_file, override=True)
        import httpx
        from ilma_api.elevenlabs import SpeechFailure

        async def run():
            async with httpx.AsyncClient(follow_redirects=False) as client:
                await generate(items, args.output, client)

        try:
            asyncio.run(run())
        except (SpeechFailure, ValueError) as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
