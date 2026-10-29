import re
import time,threading,copy
from datetime import date
from unicodedata import normalize
from typing import Literal
from typing import Optional
from pathlib import Path
from fastapi import FastAPI, Depends, Query, HTTPException, status, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from ilma_api.compression import StreamingSafeGZipMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_, inspect
from sqlalchemy.exc import SQLAlchemyError

from ilma_api.db import SessionLocal, Institution, InstitutionAlias, Release, Event, Source
from ilma_api.report_card import get_institution_report_card
from ilma_api.voice import MAX_UPLOAD_BYTES, VoiceError
from ilma_api import settings
from ilma_api.admission import ProviderAdmissionMiddleware
from ilma_api.security_headers import SecurityHeadersMiddleware

from contextlib import asynccontextmanager
_index_cache={}
_index_lock=threading.Lock()

@asynccontextmanager
async def lifespan(app):
    from ilma_api.settings import validate_environment
    validate_environment()
    from ilma_api import http_clients
    await http_clients.start()
    import asyncio
    from ilma_api.tts_warmup import warm,maintain
    background=[asyncio.create_task(warm()),asyncio.create_task(maintain())]
    try:yield
    finally:
        from ilma_api.audio_cache import get_store
        for task in background:task.cancel()
        await asyncio.gather(*background,return_exceptions=True)
        await get_store().close()
        await http_clients.stop()

app = FastAPI(lifespan=lifespan,
    title="ILMA Banking API",
    description="Factual, transparent banking health check API for Bangladesh",
    version="1.0.0"
)

app.add_middleware(ProviderAdmissionMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
# Compress text responses; text/event-stream is excluded so voice answers still stream.
app.add_middleware(StreamingSafeGZipMiddleware, minimum_size=1024)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Static assets directory
STATIC_DIR = Path(__file__).parent.parent.parent / "static"


class AppStaticFiles(StaticFiles):
    """Versioned assets are immutable; the acceptance page is hidden unless enabled."""
    async def get_response(self, path, scope):
        if path == 'voice-test.html' and not settings.VOICE_TEST_PAGE_ENABLED:
            raise HTTPException(status_code=404)
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            versioned = b'v=' in scope.get('query_string', b'')
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable' if versioned else 'public, max-age=86400'
        return response


if STATIC_DIR.exists():
    app.mount("/static", AppStaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", include_in_schema=False)
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file, headers={"Cache-Control": "no-store, no-transform"})
    return {"message": "ILMA App API is running."}

@app.get("/v1/health")
def health_check(db: Session = Depends(get_db), response: Response = None):
    try:
        rel = db.query(Release).order_by(Release.loaded_at.desc()).first()
        release_id = rel.release_id if rel else "unknown"
        tables = set(inspect(db.get_bind()).get_table_names())
        bank_ready = {'institution', 'institution_alias', 'fact', 'source', 'rate', 'insurance_rule'} <= tables
        bank_ready = bank_ready and db.query(Institution.id).first() is not None
        voice_ready = {'app_question_log', 'app_rate_counter', 'app_content'} <= tables
        if response is not None and (not bank_ready or not voice_ready):response.status_code=503
        return {
            "ok": bool(bank_ready and voice_ready),
            "release_id": release_id,
            "db": "connected",
            "bank_data_ready": bool(bank_ready),
            "voice_tables_ready": voice_ready,
        }
    except Exception as e:
        if response is not None:response.status_code=503
        return {
            "ok": False,
            "release_id": None,
            "db": "unavailable"
        }

@app.get("/v1/institutions")
def search_institutions(
    q: Optional[str] = Query(None, description="Search term for bank name or alias"),
    db: Session = Depends(get_db),
    list_mode: Optional[str] = Query(None, alias='list')
):
    if list_mode == 'demo':
        from ilma_api.bank_services import demo_banks, bank_view
        return [bank_view(db, bank) for bank in demo_banks(db,include_incident_banks=True)]
    if not q:
        insts = db.query(Institution).limit(5).all()
        return [
            {
                "id": i.id,
                "slug": i.slug,
                "name_bn": i.name_bn,
                "name_en": i.name_en,
                "type": i.type,
                "coverage": i.coverage
            }
            for i in insts
        ]
    
    # Escape LIKE wildcards so "%" or "_" searches for those characters literally.
    term = normalize('NFC', q.strip()).lower().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    query_str = f"%{term}%"
    # Search in institution names or aliases
    matched_ids = (
        db.query(InstitutionAlias.institution_id)
        .filter(InstitutionAlias.alias.ilike(query_str, escape='\\'))
        .all()
    )
    id_list = [mid[0] for mid in matched_ids]
    from ilma_api.extra_data import related_names
    from ilma_api.voice_text import normalize_alias
    query_alias=' '+normalize_alias(q)+' '
    blocked={r.parent_bank_id for r in related_names(db) if ' '+normalize_alias(r.name)+' ' in query_alias}
    
    results = (
        db.query(Institution)
        .filter(
            or_(
                Institution.name_bn.ilike(query_str, escape='\\'),
                Institution.name_en.ilike(query_str, escape='\\'),
                Institution.slug.ilike(query_str, escape='\\'),
                Institution.id.in_(id_list)
            )
        )
        .filter(~Institution.id.in_(blocked))
        .limit(5)
        .all()
    )

    return [
        {
            "id": i.id,
            "slug": i.slug,
            "name_bn": i.name_bn,
            "name_en": i.name_en,
            "type": i.type,
            "coverage": i.coverage
        }
        for i in results
    ]

@app.get("/v1/institutions/index")
def get_institution_index(db: Session = Depends(get_db)):
    key=str(db.get_bind().url)
    if db.get_bind().dialect.name=='mysql':
        with _index_lock:
            cached=_index_cache.get(key)
            if cached and cached[0]>time.monotonic():return copy.deepcopy(cached[1])
    institutions = db.query(Institution).all()
    from ilma_api.extra_data import related_names
    excluded=related_names(db)
    output = []
    for inst in institutions:
        aliases = [a.alias for a in inst.aliases]
        output.append({
            "id": inst.id,
            "slug": inst.slug,
            "name_bn": inst.name_bn,
            "name_en": inst.name_en,
            "type": inst.type,
            "coverage": inst.coverage,
            "licensed": inst.licensed,
            "aliases": aliases,
            "related_entities": [r.name for r in excluded if r.parent_bank_id==inst.id]
        })
    if db.get_bind().dialect.name=='mysql':
        with _index_lock:_index_cache[key]=(time.monotonic()+60,copy.deepcopy(output))
    return output

@app.get("/v1/institutions/{id_or_slug}/report-card")
def get_report_card(id_or_slug: str, db: Session = Depends(get_db)):
    card = get_institution_report_card(db, id_or_slug)
    if not card:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {
                "code": "not_found",
                "message_bn": "প্রতিষ্ঠানটি পাওয়া যায়নি।",
                "message_en": "Institution was not found."
            }}
        )
    return card

# Legacy pure helpers retained for regression fixtures; no public amount-taking
# calculator routes. APP_SPEC_05 calculations run entirely on the device.
def calculate_insurance(amount: float = Query(..., gt=0), type: Literal["bank", "nbfi"] = Query("bank")):
    if type == "bank":
        limit = 200000.0
        insured = min(amount, limit)
        uninsured = max(0.0, amount - limit)
        return {
            "amount": amount,
            "type": "bank",
            "insured": insured,
            "uninsured": uninsured,
            "limit": limit,
            "payout_working_days": 17,
            "law": "Deposit Protection Act 2026"
        }
    else:
        return {
            "amount": amount,
            "type": "nbfi",
            "insured": 0.0,
            "uninsured": amount,
            "limit": 0,
            "covered_from": "2028-07-01",
            "note": "Coverage starts July 1, 2028"
        }

def calculate_return(
    principal: float = Query(..., gt=0),
    rate: float = Query(..., gt=0, le=0.25),
    tenor_months: int = Query(12, ge=1, le=120),
    has_tin: bool = Query(True)
):
    gross_interest = principal * rate * (tenor_months / 12.0)
    tax_rate = 0.10 if has_tin else 0.15
    tax = gross_interest * tax_rate
    net_interest = gross_interest - tax
    inflation_rate = 0.098 # 9.8%
    inflation_loss = principal * inflation_rate * (tenor_months / 12.0)
    real_return = net_interest - inflation_loss

    return {
        "principal": principal,
        "rate": rate,
        "tenor_months": tenor_months,
        "gross_interest": round(gross_interest, 2),
        "tax_rate": tax_rate,
        "tax_deducted": round(tax, 2),
        "net_interest": round(net_interest, 2),
        "inflation_rate": inflation_rate,
        "inflation_adjustment": round(inflation_loss, 2),
        "real_return": round(real_return, 2)
    }

@app.get("/v1/news")
def get_banking_news(db: Session = Depends(get_db)):
    events = db.query(Event).order_by(Event.event_date.desc()).all()
    news_items = []
    seen=set()
    for ev in events:
        src = ev.sources[0] if ev.sources else None
        identity=(src.url if src else None,ev.title_en,str(ev.event_date))
        if identity in seen:continue
        seen.add(identity)
        news_items.append({
            "id": ev.event_id,
            "title_bn": ev.title_bn,
            "title_en": ev.title_en,
            "summary_bn": "সরকারি সূত্রে প্রকাশিত।" if ev.official else "খবরে প্রকাশিত, নিশ্চিত নয়।",
            "summary_en": "Published by an official source." if ev.official else "Reported in the news, not confirmed.",
            "official": ev.official,
            "status": ev.status,
            "date": str(ev.event_date),
            "publisher": src.publisher if src else None,
            "source_url": src.url if src else None
        })
    return news_items


@app.get('/v1/audio/{token}.mp3',include_in_schema=False)
async def voice_audio(token:str):
    from ilma_api.audio_cache import audio_response
    return await audio_response(token)


@app.get("/v1/voice/config")
def voice_config():
    from ilma_api import settings
    return {"silence_ms": settings.VOICE_SILENCE_MS, "max_ms": 15000, "no_speech_ms": 6000,"agent_no_speech_ms":8000}


async def _voice_request(request, db, mode):
    from ilma_api.voice_pipeline import parse_request, run_pipeline
    from ilma_api.voice_timings import VoiceTimings
    import time
    timings=VoiceTimings(request.scope.get('ilma_started'))
    body = bytearray()
    try:
        async for chunk in request.stream():
            if len(body) + len(chunk) > MAX_UPLOAD_BYTES:
                raise VoiceError("audio_too_large", 413, "রেকর্ডিংটি খুব বড়।", "Upload is too large.")
            body.extend(chunk)
        timings.mark('upload_done',ms=round((request.scope.get('ilma_upload_done',time.monotonic())-timings.started)*1000,2))
        audio, text, mime, context = parse_request(request.headers.get("content-type", ""), bytes(body), mode)
        body.clear()
        import hashlib, hmac
        from datetime import datetime
        from ilma_api import settings
        identifier = request.headers.get('x-ilma-device', '')[:80] or (request.client.host if request.client else 'anonymous')
        device_hash = hmac.new(settings.VOICE_LOG_SALT.encode(), (datetime.utcnow().strftime('%Y-%m') + identifier).encode(), hashlib.sha256).hexdigest()[:16]
        watch_device=request.headers.get('x-ilma-device','')
        watch_identity = hmac.new(settings.VOICE_LOG_SALT.encode(), ('watch:'+watch_device).encode(), hashlib.sha256).hexdigest() if re.fullmatch('[a-zA-Z0-9_-]{20,80}',watch_device) else None
        bind = db.get_bind()
        # Streaming opens its own session; release the request session now so
        # a slow voice stream does not hold a pooled connection for its whole
        # duration. FastAPI's dependency cleanup close after this is a safe
        # no-op on an already-closed session.
        db.close()
        async def stream_response():
            nonlocal audio
            from ilma_api.voice_diagnostics import start_capture, capture_event, save_capture
            diagnostic = start_capture(audio, mime, context.ui_lang) if mode == 'voice' else None
            # Own the session through streaming, independent of FastAPI's
            # dependency cleanup timing. Drop the outer raw-audio reference.
            with Session(bind=bind) as stream_db:
                pipeline = run_pipeline(audio, text, mime, context, lambda session=stream_db: get_institution_index(session), stream_db, mode, device_hash, diagnostic=diagnostic, watch_identity=watch_identity, timings=timings)
                audio = None
                try:
                    async for chunk in pipeline:
                        if diagnostic is not None: capture_event(diagnostic, chunk)
                        yield chunk
                finally:
                    await pipeline.aclose()
                    timings.finish()
                    if diagnostic is not None:
                        import asyncio
                        await asyncio.shield(asyncio.to_thread(save_capture,diagnostic,bind))
        return StreamingResponse(stream_response(),
            media_type="text/event-stream", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"error": {"code": "bank_data_unavailable", "message_bn": "ব্যাংকের তথ্য এখন পাওয়া যাচ্ছে না।", "message_en": "Bank data is unavailable."}})
    except VoiceError as error:
        return JSONResponse(status_code=error.status, content={"error": {"code": error.code, "message_bn": error.bn, "message_en": error.en}})
    finally:
        body.clear()


@app.post("/v1/voice")
async def voice_input(request: Request, db: Session = Depends(get_db)):
    return await _voice_request(request, db, "voice")


@app.post("/v1/ask")
async def ask_voice(request: Request, db: Session = Depends(get_db)):
    # APP_SPEC_02: typed input uses the same matcher/intent/result pipeline.
    return await _voice_request(request, db, "text")


from pydantic import BaseModel, model_validator

class ReadoutRequest(BaseModel):
    kind: Literal['report_card', 'insurance', 'news', 'ivr', 'reasons', 'sources', 'agent_question']
    agent_state: Literal['BANK','DETAIL','FIGURES','HISTORY','SERVICES','SERVICE','COMPARE','NEXT','ASK_BANK','WATCH_CONFIRM'] | None = None
    prompt: Literal['ivr_open', 'ivr_mic', 'ivr_lang', 'ivr_menu', 'ivr_name', 'ivr_confirm', 'ivr_next', 'ivr_chose_bn', 'ivr_chose_en', 'ivr_chose_bank', 'ivr_chose_services', 'ivr_yes', 'ivr_no', 'ivr_ready', 'ivr_repeat_hint'] | None = None
    institution_id: int | None = None
    language: Literal['bn', 'en'] = 'bn'

    @model_validator(mode='after')
    def guided_prompt_scope(self):
        if (self.kind == 'agent_question') != (self.agent_state is not None):
            raise ValueError('A script state is required only for agent question readouts.')
        if (self.kind == 'ivr') != (self.prompt is not None):
            raise ValueError('Guided readouts require an allowlisted prompt; other readouts do not accept prompts.')
        return self


@app.post('/v1/speech')
async def speech_readout(payload: ReadoutRequest, db: Session = Depends(get_db)):
    from ilma_api.voice_pipeline import readout
    try:
        result = await readout(payload.kind, payload.institution_id, payload.language, db, payload.prompt, payload.agent_state)
        if not result['audio_url']:
            return JSONResponse(status_code=503, content={'error': {'code': 'speech_unavailable',
                'message_bn': 'পড়ে শোনানোর সেবা এখন চালু নেই।', 'message_en': 'Spoken playback is not available.'}})
        return result
    except (SQLAlchemyError, ValueError):
        return JSONResponse(status_code=503, content={'error': {'code': 'bank_data_unavailable',
            'message_bn': 'ব্যাংকের তথ্য এখন পাওয়া যাচ্ছে না।', 'message_en': 'Bank data is unavailable.'}})


@app.get('/v1/content/fixed')
def fixed_voice_content():
    from ilma_api.voice_assets import load_approved
    try:
        manifest = load_approved(STATIC_DIR / 'audio/fixed', allow_legacy=True)
        return {'clips': {key: {'url': '/static/audio/fixed/' + item['file'], 'fallback_url': '/static/audio/fixed/' + item['fallback_file'], 'text': item['text']} for key, item in manifest['clips'].items()}}
    except (ValueError, OSError, KeyError):
        return {'clips': {}}


@app.get('/sw.js', include_in_schema=False)
def service_worker():
    return FileResponse(STATIC_DIR / 'sw.js', media_type='application/javascript',
                        headers={'Cache-Control': 'no-cache', 'Service-Worker-Allowed': '/'})


@app.get('/favicon.ico', include_in_schema=False)
def favicon():
    return FileResponse(STATIC_DIR / 'icons/favicon.ico', media_type='image/x-icon', headers={'Cache-Control': 'public, max-age=604800'})


@app.get('/manifest.webmanifest', include_in_schema=False)
def web_manifest():
    return FileResponse(STATIC_DIR / 'manifest.webmanifest', media_type='application/manifest+json', headers={'Cache-Control': 'public, max-age=86400'})


@app.get('/voice-test', include_in_schema=False)
def voice_acceptance_page():
    # Physical-device acceptance page: off unless explicitly enabled for a test window.
    if not settings.VOICE_TEST_PAGE_ENABLED:
        raise HTTPException(status_code=404)
    return FileResponse(STATIC_DIR / 'voice-test.html', headers={'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex'})


from ilma_api.bank_services import make_router
app.include_router(make_router(get_db))

from ilma_api.extra_routes import router as extra_router
app.include_router(extra_router(get_db))
