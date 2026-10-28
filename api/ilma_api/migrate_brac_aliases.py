"""Add user-approved BRAC ASR spellings without changing source names or facts."""
from ilma_api.db import engine, SessionLocal, Institution, InstitutionAlias

ALIASES = [('breakbank','en'),('break bank','en'),('ব্রেক ব্যাংক','bn')]
SOURCE = 'user_report_2026-10-28'


def add_aliases(db):
    bank=db.query(Institution).filter_by(slug='bracbank').one_or_none()
    if bank is None:return 0
    added=0
    for alias,language in ALIASES:
        if db.query(InstitutionAlias.id).filter_by(institution_id=bank.id,alias=alias).first():continue
        values=dict(institution_id=bank.id,alias=alias,lang=language,source=SOURCE)
        if db.get_bind().dialect.name=='mysql':
            from sqlalchemy.dialects.mysql import insert
            table=InstitutionAlias.__table__
            db.execute(insert(table).values(**values).on_duplicate_key_update(id=table.c.id))
        else:db.add(InstitutionAlias(**values))  # Isolated SQLite fixtures only.
        db.flush();added+=1
    return added


def migrate():
    if engine.dialect.name!='mysql' or engine.url.database!='ilma':raise ValueError('Alias migration requires the ilma MySQL database.')
    with SessionLocal() as db:
        if not db.query(Institution.id).filter_by(slug='bracbank').first():raise ValueError('Load the existing BRAC bank first.')
        count=add_aliases(db);db.commit()
    print(f'BRAC aliases ready in ilma; added {count}. No bank facts changed.')


if __name__=='__main__':
    try:migrate()
    except Exception:raise SystemExit('BRAC alias migration failed; verify ilma access. Credentials were not printed.') from None
