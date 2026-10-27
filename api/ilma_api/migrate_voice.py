"""Non-destructive MySQL schema/alias migration for APP_SPEC_02. Never imports facts."""
import re
from sqlalchemy import inspect, text
from ilma_api.db import engine, Base, SessionLocal, Institution, InstitutionAlias, AppQuestionLog, AppRateCounter, AppContent
from ilma_api.voice_text import normalize_alias

DEMO_ALIASES = [
    (r'\beastern\b', ['EBL', 'ইবিএল', 'Eastern Bank']),
    (r'\bbrac\b', ['BRAC', 'ব্র্যাক', 'brac bank']),
    (r'\bcity\s+bank\b', ['City', 'City Bank', 'সিটি ব্যাংক']),
    (r'\bmutual\s+trust\b|\bmtb\b', ['MTB', 'এমটিবি', 'Mutual Trust Bank']),
    (r'\bncc\b|national credit (?:and|&) commerce', ['NCC', 'এনসিসি', 'NCC Bank']),
    (r'\bprime\s+bank\b', ['Prime', 'Prime Bank', 'প্রাইম ব্যাংক']),
    (r'dutch[ -]*bangla', ['DBBL', 'ডিবিবিএল', 'dutch bangla', 'ডাচ বাংলা ব্যাংক']),
    (r'\bbank\s+asia\b', ['Bank Asia', 'ব্যাংক এশিয়া']),
    (r'\bsbac\b|south bangla agriculture', ['SBAC', 'এসবিএসি', 'SBAC Bank']),
]

MISHEARINGS = {
    'pubali': ['উবালি', 'কুবালি', 'ভ্যালি'],
    'mercantile': ['arcantile'],
    'al arafah': ['আল-আরাফাহ Islami Bank'],
    'janata': ['জনতা ব্যাংক', 'जनता बैंक'],
}


def add_aliases(db):
    added = 0
    for bank in db.query(Institution).all():
        names = ' '.join(normalize_alias(name) for name in (bank.name_en, bank.name_bn))
        aliases = [bank.name_en, bank.name_bn]
        for pattern, variants in DEMO_ALIASES:
            if re.search(pattern, bank.name_en, re.I): aliases += variants
        for key, variants in MISHEARINGS.items():
            if key in names or (key == 'pubali' and 'পূবালী' in names): aliases += variants
        existing = {row.alias for row in bank.aliases}
        for alias in aliases:
            if alias not in existing:
                if db.get_bind().dialect.name == 'mysql':
                    # Compare with the database collation, which can consider
                    # differently cased or accented spellings equivalent.
                    from sqlalchemy.dialects.mysql import insert
                    table = InstitutionAlias.__table__
                    statement = insert(table).values(institution_id=bank.id, alias=alias,
                        lang='bn' if any('\u0900' <= c <= '\u09ff' for c in alias) else 'en',
                        source='asr_test_2026-10-25')
                    statement = statement.on_duplicate_key_update(id=table.c.id)
                    before = db.query(InstitutionAlias.id).filter_by(institution_id=bank.id, alias=alias).first()
                    db.execute(statement)
                    existing.add(alias)
                    added += int(before is None)
                    continue
                db.add(InstitutionAlias(institution_id=bank.id, alias=alias,
                    lang='bn' if any('\u0900' <= c <= '\u09ff' for c in alias) else 'en', source='asr_test_2026-10-25'))
                existing.add(alias)
                added += 1
    return added


def migrate():
    if engine.dialect.name != 'mysql': raise SystemExit('Voice runtime migration requires MySQL.')
    schema = inspect(engine)
    if not schema.has_table('institution') or not schema.has_table('institution_alias'):
        raise SystemExit('Create/load the verified bank schema first; no sample institutions will be inserted.')
    columns = {column['name'] for column in schema.get_columns('institution_alias')}
    if 'source' not in columns:
        with engine.begin() as connection:
            connection.execute(text('ALTER TABLE institution_alias ADD COLUMN source VARCHAR(64) NULL'))
    AppQuestionLog.__table__.create(engine, checkfirst=True)
    AppRateCounter.__table__.create(engine, checkfirst=True)
    AppContent.__table__.create(engine, checkfirst=True)
    if 'created_at' not in {column['name'] for column in inspect(engine).get_columns('app_question_log')}:
        with engine.begin() as connection:
            connection.execute(text('ALTER TABLE app_question_log ADD COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP'))
    with SessionLocal() as db:
        count = add_aliases(db)
        from ilma_api.voice_glossary import add_glossary
        content_count = add_glossary(db)
        db.commit()
    print(f'Voice migration complete; added {count} aliases and {content_count} authored glossary entries. No bank facts changed.')


if __name__ == '__main__':
    try: migrate()
    except Exception:
        raise SystemExit('MySQL migration failed. Check DATABASE_URL, database access and schema permissions; credentials were not printed.') from None
