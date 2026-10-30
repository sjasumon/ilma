"""Shared card identity and deterministic, source-bound display conditions."""
import csv,re
from pathlib import Path
from decimal import Decimal

def field(row,name,default=''):
    return row.get(name,default) if isinstance(row,dict) else getattr(row,name,default)

def clean_name(row):
    text=re.sub(r'[\u0980-\u09ff]+',' ',field(row,'column_header'))
    text=re.sub(r'\b(?:Visa|Mastercard|Master\s+Card|Amex|For|Card)\b',' ',text,flags=re.I)
    return re.sub(r'\s+',' ',text).strip(' -·') or field(row,'tier') or 'Card'

def card_key(row):
    bank=field(row,'institution_id',None) or field(row,'bank_id')
    return ':'.join(str(v).casefold() for v in [bank,field(row,'network'),field(row,'tier'),clean_name(row)])

NETWORKS={'Visa':'ভিসা','Mastercard':'মাস্টারকার্ড','MasterCard':'মাস্টারকার্ড','Amex':'অ্যামেক্স'}
TIERS={'Classic':'ক্লাসিক','Gold':'গোল্ড','Platinum':'প্লাটিনাম','Signature':'সিগনেচার','Titanium':'টাইটানিয়াম','World':'ওয়ার্ল্ড','World Elite':'ওয়ার্ল্ড এলিট','Infinite':'ইনফিনিট','Silver':'সিলভার','Green':'গ্রিন','Blue':'ব্লু','Black':'ব্ল্যাক','Standard':'স্ট্যান্ডার্ড'}

def display(row):
    network=field(row,'network');tier=field(row,'tier');clean=clean_name(row)
    return {'card_key':card_key(row),'card_display_bn':' '.join([NETWORKS.get(network,network),TIERS.get(tier,tier)]),'card_display_en':' '.join([network or '',tier or '']).strip(),'card_printed_name':clean if clean.casefold()!=(tier or '').casefold() else ''}

RULES=list(csv.DictReader((Path(__file__).resolve().parents[2]/'seed/condition_bn_map.csv').open(encoding='utf-8')))
BN=str.maketrans('0123456789','০১২৩৪৫৬৭৮৯')

def condition(row,renewal=False,language='bn'):
    attribute=field(row,'attribute');value=field(row,'value_text') or field(row,'value')
    text=re.sub(r'\bstale\s*;?','',field(row,'condition'),flags=re.I).strip()+' '+value
    if attribute=='supplementary_card_fee' and value.casefold() in {'free','0'}:return 'প্রথম অতিরিক্ত কার্ড বিনামূল্যে' if language=='bn' else 'First supplementary card free'
    if attribute=='fee_waiver_rule' and field(row,'unit')=='count':text+=' waived if '+value+' transactions'
    for rule in RULES:
        if rule['attribute'] and rule['attribute']!=attribute:continue
        if rule['id']=='first_year' and not renewal:continue
        match=re.search(rule['pattern'],text,re.I)
        if not match:continue
        values={key:(val or '').replace(',','') for key,val in match.groupdict().items()}
        if rule['id']=='higher':
            pct=re.search(r'(\d+(?:\.\d+)?)\s*%',text);money=re.search(r'(?:BDT|Tk\.?)\s*([\d,]+)',text,re.I)
            if not pct or not money:continue
            values={'x':pct[1],'y':money[1].replace(',','')}
        rendered=rule['bn' if language=='bn' else 'en'].format(**values)
        return rendered.translate(BN) if language=='bn' else rendered
    return ''

def numeric(row):
    if field(row,'value_num',None) is not None:return Decimal(str(field(row,'value_num')))
    text=(field(row,'value_text') or field(row,'value')).strip()
    if text.casefold() in {'free','0'}:return Decimal(0)
    match=re.fullmatch(r'(\d+(?:\.\d+)?)\s*%',text)
    if match:
        # A percentage may be stored as text; do not invent unsupported numbers.
        value=Decimal(match[1])
        from ilma_api.export_seed import quote_numbers
        if value in quote_numbers(field(row,'quote')):return value
    return None
