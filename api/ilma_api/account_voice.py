"""Short, source-bound account fee answers; never reuse credit/DPS facts."""
from ilma_api.account_catalog import banks,calculate
from ilma_api.human_tokens import spoken_name

def answer(db,bank_id,debit,language):
    bn=language=='bn';bank=next((b for b in banks(db) if b['id']==bank_id),None)
    if bank is None:return ('এই ব্যাংকের প্রকাশিত হিসাবের ফির তথ্য এখানে নেই।' if bn else 'Published account-fee information for this bank is unavailable here.'),[]
    name=spoken_name(bank['name_bn' if bn else 'name_en']);parts=[];facts=[]
    def add(row,label_bn,label_en,period_bn='',period_en=''):
        if not row or row.get('value_num') is None or not row.get('unit','').startswith('bdt'):return
        value=f"{row['value_num']:g}"
        vat=('; এতে ভ্যাট অন্তর্ভুক্ত' if bn else '; VAT is included') if row.get('vat_included') else (f"; সঙ্গে {row['vat_percent']:g}% ভ্যাটের শর্ত আছে" if bn else f"; the source specifies {row['vat_percent']:g}% VAT") if row.get('vat_percent') else ''
        maximum=('সর্বোচ্চ ' if bn else 'up to ') if row.get('rate_is_maximum') else ''
        text=(f'{label_bn} {period_bn}{maximum}{value} টাকা' if bn else f'{label_en} is {maximum}{value} taka{period_en}')+vat+('।' if bn else '.')
        parts.append(text)
        facts.append(dict(fact_id=row['offer_id'],institution_id=bank_id,kind='account_fee',values=row,text_bn=text if bn else '',text_en=text if not bn else '',source=dict(source_url=row['source_url'],source_title=row.get('source_title') or row['product'],quote=row['quote'],page=row.get('page'),published_at=str(row['doc_date']),condition=row['condition'])))
    if debit:
        add(bank['debit_main'],'সাধারণ ডেবিট কার্ডের মূল বার্ষিক ফি','The standard debit card’s base annual fee')
        add(bank['debit_replacement'],'ওই কার্ডের বদলি ফি','Its replacement fee')
    else:
        # This is the documented fixed example, not an inferred personal balance.
        fee=calculate(bank,100000,False,False)['maintenance']
        if fee:parts.append('এক লাখ টাকার স্থির নমুনায়' if bn else 'For the fixed 1-lakh-taka example,')
        add(fee,'রক্ষণাবেক্ষণের মূল ফি','the base maintenance fee','ছয় মাসে ',' per half year')
        sms=bank['sms']
        import re
        half=bool(sms and sms['periods_per_year']==2)
        annual=bool(sms and (sms['unit']=='bdt_year' or re.search(r'annual|yearly|per year|per annum',sms['condition']+' '+sms['quote'],re.I)))
        add(sms,'এসএমএসের মূল ফি','The base SMS fee','ছয় মাসে ' if half else 'বছরে ' if annual else '', ' per half year' if half else ' per year' if annual else '')
    if not facts:return ('এই বিভাগের নির্ভরযোগ্য প্রকাশিত ফির তথ্য এখানে নেই। অজানা ফি শূন্য ধরে নিচ্ছি না।' if bn else 'Reliable published fees for this category are unavailable here. Unknown fees are not assumed to be zero.'),[]
    parts.append('নির্দিষ্ট হিসাবের শর্ত প্রযোজ্য।' if bn else 'The specific account’s conditions apply.')
    return (name+'। ' if bn else name+'. ')+' '.join(parts),facts
