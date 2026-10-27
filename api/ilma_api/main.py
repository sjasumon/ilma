from datetime import date
from unicodedata import normalize
from typing import Literal
from typing import Optional
from pathlib import Path
from fastapi import FastAPI, Depends, Query, HTTPException, status, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from ilma_api.db import SessionLocal, Institution, InstitutionAlias, Release, Event, Source
from ilma_api.report_card import get_institution_report_card
from ilma_api.voice import MAX_UPLOAD_BYTES, VoiceError

app = FastAPI(
    title="ILMA Banking API",
    description="Factual, transparent banking health check API for Bangladesh",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Static assets directory
STATIC_DIR = Path(__file__).parent.parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", include_in_schema=False)
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file, headers={"Cache-Control": "no-store"})
    return {"message": "ILMA App API is running."}

@app.get("/v1/health")
def health_check(db: Session = Depends(get_db)):
    try:
        rel = db.query(Release).order_by(Release.loaded_at.desc()).first()
        release_id = rel.release_id if rel else "unknown"
        return {
            "ok": True,
            "release_id": release_id,
            "db": "connected"
        }
    except Exception as e:
        return {
            "ok": False,
            "release_id": None,
            "db": "unavailable"
        }

@app.get("/v1/institutions")
def search_institutions(
    q: Optional[str] = Query(None, description="Search term for bank name or alias"),
    db: Session = Depends(get_db)
):
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
    
    query_str = f"%{normalize('NFC', q.strip()).lower()}%"
    # Search in institution names or aliases
    matched_ids = (
        db.query(InstitutionAlias.institution_id)
        .filter(InstitutionAlias.alias.ilike(query_str))
        .all()
    )
    id_list = [mid[0] for mid in matched_ids]
    
    results = (
        db.query(Institution)
        .filter(
            or_(
                Institution.name_bn.ilike(query_str),
                Institution.name_en.ilike(query_str),
                Institution.slug.ilike(query_str),
                Institution.id.in_(id_list)
            )
        )
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
    institutions = db.query(Institution).all()
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
            "aliases": aliases
        })
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

@app.get("/v1/services/insurance-split")
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

@app.get("/v1/services/calculate-return")
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
    for ev in events:
        src = ev.sources[0] if ev.sources else None
        news_items.append({
            "id": ev.event_id,
            "title_bn": ev.title_bn,
            "title_en": ev.title_en,
            "summary_bn": f"বাংলাদেশ ব্যাংকের সাম্প্রতিক সিদ্ধান্ত ও সার্কুলার অনুযায়ী {ev.title_bn}।",
            "summary_en": f"Under recent regulatory framework, {ev.title_en}.",
            "official": ev.official,
            "status": ev.status,
            "date": str(ev.event_date),
            "publisher": src.publisher if src else "বাংলাদেশ ব্যাংক",
            "source_url": src.url if src else None
        })
    return news_items


@app.get("/v1/voice/config")
def voice_config():
    from ilma_api import settings
    return {"silence_ms": settings.VOICE_SILENCE_MS, "max_ms": 15000, "no_speech_ms": 6000}


async def _voice_request(request, db, mode):
    from ilma_api.voice_pipeline import parse_request, run_pipeline
    body = bytearray()
    try:
        async for chunk in request.stream():
            if len(body) + len(chunk) > MAX_UPLOAD_BYTES:
                raise VoiceError("audio_too_large", 413, "রেকর্ডিংটি খুব বড়।", "Upload is too large.")
            body.extend(chunk)
        audio, text, mime, context = parse_request(request.headers.get("content-type", ""), bytes(body), mode)
        body.clear()
        import hashlib, hmac
        from datetime import datetime
        from ilma_api import settings
        identifier = request.headers.get('x-ilma-device', '')[:80] or (request.client.host if request.client else 'anonymous')
        device_hash = hmac.new(settings.VOICE_LOG_SALT.encode(), (datetime.utcnow().strftime('%Y-%m') + identifier).encode(), hashlib.sha256).hexdigest()[:16]
        bind = db.get_bind()
        async def stream_response():
            nonlocal audio
            # Own the session through streaming, independent of FastAPI's
            # dependency cleanup timing. Drop the outer raw-audio reference.
            with Session(bind=bind) as stream_db:
                pipeline = run_pipeline(audio, text, mime, context, lambda: get_institution_index(stream_db), stream_db, mode, device_hash)
                audio = None
                try:
                    async for chunk in pipeline: yield chunk
                finally:
                    await pipeline.aclose()
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


from pydantic import BaseModel

class ReadoutRequest(BaseModel):
    kind: Literal['report_card', 'insurance', 'news']
    institution_id: int | None = None
    language: Literal['bn', 'en'] = 'bn'


@app.post('/v1/speech')
async def speech_readout(payload: ReadoutRequest, db: Session = Depends(get_db)):
    from ilma_api.voice_pipeline import readout
    try:
        result = await readout(payload.kind, payload.institution_id, payload.language, db)
        if not result['audio_url']:
            return JSONResponse(status_code=503, content={'error': {'code': 'speech_unavailable',
                'message_bn': 'পড়ে শোনানোর সেবা এখন চালু নেই।', 'message_en': 'Spoken playback is not available.'}})
        return result
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={'error': {'code': 'bank_data_unavailable',
            'message_bn': 'ব্যাংকের তথ্য এখন পাওয়া যাচ্ছে না।', 'message_en': 'Bank data is unavailable.'}})


@app.get('/v1/content/fixed')
def fixed_voice_content():
    from ilma_api.voice_assets import load_approved
    try:
        manifest = load_approved(STATIC_DIR / 'audio/fixed')
        return {'clips': {key: {'url': '/static/audio/fixed/' + item['file'], 'fallback_url': '/static/audio/fixed/' + item['fallback_file'], 'text': item['text']} for key, item in manifest['clips'].items()}}
    except (ValueError, OSError, KeyError):
        return {'clips': {}}


@app.get('/sw.js', include_in_schema=False)
def service_worker():
    return FileResponse(STATIC_DIR / 'sw.js', media_type='application/javascript',
                        headers={'Cache-Control': 'no-cache', 'Service-Worker-Allowed': '/'})


@app.get('/voice-test', include_in_schema=False)
def voice_acceptance_page():
    return FileResponse(STATIC_DIR / 'voice-test.html', headers={'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex'})
