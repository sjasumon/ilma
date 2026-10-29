"""Explicit paid-Meta evaluation of frozen preview code; no TTS generation."""
import argparse,hashlib,json,os,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
import httpx
from dotenv import load_dotenv
from evaluate_human_voice import evaluate_v2
from phase1_gate import database_auditor,gate

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true');parser.add_argument('--sample',action='store_true')
    parser.add_argument('--app-dir',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--base-url',default='http://127.0.0.1:8019');parser.add_argument('--workers',type=int,default=2,choices=[1,2])
    args=parser.parse_args()
    if not args.live:parser.error('--live is required: real Meta requests incur provider usage')
    url=urlparse(args.base_url)
    if url.hostname not in {'127.0.0.1','localhost'} or url.port in {None,80,443,8001,8018}:parser.error('Use a separate local evaluation service, not production or the public preview')
    app=args.app_dir.resolve();environment=app/'.env'
    for key in list(os.environ):
        if key.upper().startswith('DB_') or key.upper()=='DATABASE_URL':del os.environ[key]
    load_dotenv(environment,override=True)
    os.environ.update(ELEVENLABS_API_KEY='',TTS_PREWARM='false')
    sys.path.insert(0,str(app/'api'))
    from ilma_api import settings
    settings.validate_environment()
    sha=lambda:subprocess.check_output(['git','-C',str(app),'rev-parse','HEAD'],text=True).strip()
    clean=lambda:subprocess.check_output(['git','-C',str(app),'status','--porcelain'],text=True).strip()==''
    commit=sha()
    if not clean():raise RuntimeError('The evaluated checkout must be clean and frozen')
    source=app/'tests/human_voice_cases_v2.json';cases=json.loads(source.read_text())
    if len({case['id'] for case in cases})!=len(cases):raise RuntimeError('Corpus case IDs must be unique')
    with httpx.Client(base_url=args.base_url,timeout=10) as client:
        response=client.get('/v1/health');response.raise_for_status();release=response.json().get('release_id')
        banks=client.get('/v1/institutions/index').json()
    args.output.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    # evaluate_v2 retains partial results on failure. Its old 95% return value
    # is not used as Phase 1's result: every explicit Phase 1 gate is below.
    evaluate_v2(args.base_url,cases,args.output,workers=args.workers,sample=args.sample,auditor=database_auditor(banks))
    report=json.loads(args.output.read_text())
    report.update(evaluated_commit=commit,runtime_source_unchanged=sha()==commit and clean(),evaluated_at_utc=datetime.now(timezone.utc).isoformat(),corpus_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),latency_definition='Send to first checked answer sentence or completed control reply; full completion recorded separately',tts_generation=False)
    report['phase1']=gate(report)
    report['audited_facts']=sum(r['claim_audit']['facts_checked'] for r in report['cases'])
    report['audited_sentences']=sum(r['claim_audit']['sentences_checked'] for r in report['cases'])
    report['data_release']=release
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');args.output.chmod(0o600)
    print(json.dumps({key:value for key,value in report.items() if key!='cases'},ensure_ascii=False,indent=2),flush=True)
    return 0 if report['phase1']['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
