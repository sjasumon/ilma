"""Extra publication endpoints. Watched-bank responses are never cached."""
import hashlib,hmac,re
from datetime import date
import calendar
from fastapi import APIRouter,Depends,HTTPException,Query,Request
from fastapi.responses import JSONResponse
from ilma_api.db import Institution,AppWatchItem
from ilma_api.extra_data import items,view,available,ExtraItem
from ilma_api import settings

def router(get_db):
    api=APIRouter()
    @api.get('/v1/institutions/{bank_id}/publications/{kind}')
    def publications(bank_id:int,kind:str,page:int=Query(1,ge=1),db=Depends(get_db)):
        if not db.get(Institution,bank_id):raise HTTPException(404,'Bank not found')
        if kind not in {'announcements','reports','bb-notices'}:raise HTTPException(404,'Publication type not found')
        rows=items(db,{'announcements':'announcement','reports':'report','bb-notices':'bank_notice'}[kind],bank_id)
        return dict(items=[view(r) for r in rows[(page-1)*20:page*20]],total=len(rows),page=page)
    @api.get('/v1/extra-news')
    def news(request:Request,db=Depends(get_db)):
        device=request.headers.get('x-ilma-device','')
        watched=[]
        if re.fullmatch('[a-zA-Z0-9_-]{20,80}',device):
            identity=hmac.new(settings.VOICE_LOG_SALT.encode(),('watch:'+device).encode(),hashlib.sha256).hexdigest()
            watched=[r.institution_id for r in db.query(AppWatchItem).filter_by(device_hash=identity)]
        announcements=[]
        if watched and available(db):
            announcements=[view(r) for r in db.query(ExtraItem).filter(ExtraItem.kind=='announcement',ExtraItem.institution_id.in_(watched)).order_by(ExtraItem.published_on.desc(),ExtraItem.item_id).limit(50)]
        today=date.today();cutoff=today.replace(year=today.year-1,day=min(today.day,calendar.monthrange(today.year-1,today.month)[1]))
        return JSONResponse(dict(warnings=[view(r) for r in items(db,'press')],rules=[view(r) for r in items(db,'rule') if r.published_on and cutoff<=r.published_on<=today],
            announcements=announcements,watching=bool(watched)),headers={'Cache-Control':'no-store','Vary':'X-ILMA-Device'})
    return api
