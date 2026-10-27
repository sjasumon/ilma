"""Sourced incident views. Reports are not promoted to regulator findings."""
from datetime import date
from sqlalchemy import inspect
from ilma_api.db import BankIncident
from ilma_api.rules.reasons import format_date

STATUS_LABELS = {
    'reported': ('প্রকাশিত খবর','Reported'),
    'alleged': ('অভিযোগের খবর','Allegation reported'),
    'case_filed': ('মামলা দায়েরের খবর','Case filing reported'),
    'charged': ('চার্জশিটের খবর','Charges reported'),
    'convicted': ('দণ্ডের খবর','Conviction reported'),
    'settled': ('নিষ্পত্তির খবর','Settlement reported'),
    'acquitted': ('খালাসের খবর','Acquittal reported'),
    'case_withdrawn': ('মামলা প্রত্যাহারের খবর','Case withdrawal reported'),
}
TYPE_LABELS = {
    'acc_case': ('দুর্নীতি মামলার খবর','Corruption case report'),
    'embezzlement': ('অর্থ আত্মসাতের অভিযোগ','Embezzlement allegation'),
    'loan_scam': ('ঋণ বিতরণ নিয়ে অভিযোগ','Credit-disbursement allegation'),
    'bb_penalty': ('নিয়ন্ত্রক জরিমানার খবর','Regulatory penalty report'),
    'bb_board_action': ('পর্ষদ পুনর্গঠনের খবর','Board reconstitution report'),
    'court_order': ('আদালতের আদেশ','Court order'),
    'audit_warning': ('নিরীক্ষকের পর্যবেক্ষণ','Auditor observation'),
    'liquidity_support': ('তারল্য সহায়তার খবর','Liquidity-support report'),
    'cyber_incident': ('সাইবার ঘটনার খবর','Cyber incident report'),
}


def records(db, institution_id):
    # Older schema/readiness fixtures are valid until the supplement is installed.
    if not inspect(db.connection()).has_table(BankIncident.__tablename__): return []
    return db.query(BankIncident).filter_by(institution_id=institution_id).filter(
        BankIncident.status!='single_source').order_by(BankIncident.last_update_on.desc(),BankIncident.incident_id).all()


def source_view(link):
    source=link.source
    return dict(source_id=source.source_id,source_url=source.url,source_title=source.title,
        published_at=str(source.published_at) if source.published_at else None,page=source.page,
        quote=link.quote,checked=source.checked_by.casefold()=='sumon')


def view(row, today=None):
    today=today or date.today()
    label=STATUS_LABELS.get(row.status,STATUS_LABELS['reported'])
    kind=TYPE_LABELS.get(row.kind,('ঘটনা','Incident'))
    return dict(incident_id=row.incident_id,kind=row.kind,title_bn=row.title_bn,title_en=row.title_en,
        status=row.status,status_label_bn=label[0],status_label_en=label[1],type_label_bn=kind[0],type_label_en=kind[1],
        official=row.official,confirmation_bn='প্রাথমিক নথিতে প্রকাশিত' if row.official else 'খবরে প্রকাশিত, নিশ্চিত নয়',
        confirmation_en='Published in a primary document' if row.official else 'Reported in the news, not confirmed',
        started_on=str(row.started_on) if row.started_on else None,first_reported_on=str(row.first_reported_on),
        last_update_on=str(row.last_update_on),affects_status=False,older_history=(today-row.first_reported_on).days>730,
        sources=[source_view(link) for link in row.sources],
        changes=[dict(status=change.status,status_label_bn=STATUS_LABELS[change.status][0],status_label_en=STATUS_LABELS[change.status][1],
            changed_on=str(change.changed_on),quote=change.quote,source_url=change.source.url)
            for change in sorted(row.changes,key=lambda c:(c.changed_on,c.change_id))])


def history(db,institution_id):
    rows=records(db,institution_id)
    return dict(available=bool(rows),window=None,complete_search=False,
        record_window=dict(start=str(min(r.first_reported_on for r in rows)),end=str(max(r.last_update_on for r in rows))) if rows else None,
        items=[view(row) for row in rows],
        message_bn='সরবরাহকৃত ঘটনার নথি; পূর্ণ অনুসন্ধানের সময়সীমা দেওয়া হয়নি। এটি সম্পূর্ণ ইতিহাস নয়।' if rows else 'এই ব্যাংকের ঘটনার নথি এই রপ্তানিতে নেই। পূর্ণ ইতিহাস যাচাই করা হয়নি।',
        message_en='Supplied incident records; no complete search window was provided. This is not a complete history.' if rows else 'This export supplied no incident records for this bank. Its complete history has not been checked.')


def voice_facts(db,institution_id,language):
    result=[]
    for row in records(db,institution_id)[:3]:
        item=view(row);source=item['sources'][0]
        bn=language=='bn'
        confirmation=item['confirmation_bn' if bn else 'confirmation_en'] if row.official or bn else 'Reported, unconfirmed.'
        text=(confirmation+'। '+item['title_bn' if bn else 'title_en']+' — '+item['status_label_bn' if bn else 'status_label_en']+
            ' ('+format_date(row.last_update_on,bn=bn)+')')
        result.append(dict(text=text,unconfirmed=not row.official,fact_id=row.incident_id,source_url=source['source_url'],
            source_title=source['source_title'],published_at=source['published_at'],page=source['page']))
    return result
