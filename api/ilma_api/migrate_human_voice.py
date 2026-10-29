"""Additive schema migration and derived service terms. No bank fact import."""
from sqlalchemy import inspect,text
from sqlalchemy.orm import Session
from ilma_api.db import engine,BankProfile,AppConversation,AppVoiceVariant,ServiceOffer
from ilma_api.service_terms import parse_terms

def migrate(bind=engine):
    if bind.dialect.name!='mysql' or bind.url.database!='ilma':raise ValueError('Only the ilma MySQL database is permitted')
    existing={c['name'] for c in inspect(bind).get_columns('service_offer')}
    with bind.begin() as connection:
        for name,sql in [('tenor_min_months','INT NULL'),('tenor_max_months','INT NULL'),('tenor_options','JSON NULL')]:
            if name not in existing:connection.execute(text('ALTER TABLE service_offer ADD COLUMN '+name+' '+sql))
        if 'failure_reason' not in {c['name'] for c in inspect(bind).get_columns('app_model_call')}:
            connection.execute(text('ALTER TABLE app_model_call ADD COLUMN failure_reason VARCHAR(255) NULL'))
    BankProfile.__table__.create(bind,checkfirst=True);AppConversation.__table__.create(bind,checkfirst=True)
    AppVoiceVariant.__table__.create(bind,checkfirst=True)
    with Session(bind) as db:
        rows=db.query(ServiceOffer).all()
        for row in rows:
            for key,value in parse_terms(row.product,row.condition,row.tenor_months).items():setattr(row,key,value)
        db.commit()
    print('Human voice schema ready; derived terms updated. No financial values or source quotations changed.')
if __name__=='__main__':migrate()
