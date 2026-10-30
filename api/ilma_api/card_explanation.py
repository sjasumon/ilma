"""Readable, selected-fact card explanations; independent of saved overview audio."""
from ilma_api.rules.reasons import format_number,format_date,to_bn_digits
import re
from ilma_api.service_clips import SHORT,GEN
from ilma_api.card_catalog import display

EN_SHORT={'ebl':'Eastern Bank','bracbank':'BRAC Bank','citybank':'City Bank','dutchbangl':'Dutch-Bangla Bank','bankasia':'Bank Asia','nccbank':'NCC Bank','primebank':'Prime Bank','mtb':'Mutual Trust Bank','sbacbank':'South Bangla Bank'}

LABELS={
 'annual_fee':('বার্ষিক ফি','Annual fee','কার্ড রাখার জন্য প্রতি বছর যে ফি প্রকাশিত আছে। মওকুফ ও নবায়নের শর্ত আলাদাভাবে দেখুন।','The published yearly cost of keeping the card. Check waiver and renewal conditions separately.'),
 'interest_rate':('সুদের হার','Interest rate','এটি প্রকাশিত বার্ষিক সুদের হার। কখন সুদ প্রযোজ্য হবে, তা বিল ও নগদ তোলার শর্তের ওপর নির্ভর করে।','This is the published annual interest rate. Its application depends on bill and cash-withdrawal conditions.'),
 'late_fee':('বিলম্ব ফি','Late fee','বিল দিতে দেরি হলে যে ফি প্রযোজ্য হতে পারে। এটি বার্ষিক ফি ও সুদের হার থেকে আলাদা।','The published charge for late payment, separate from annual fees and interest.'),
 'cash_advance_fee':('নগদ তোলার ফি','Cash withdrawal fee','শতাংশের হার, টাকার ন্যূনতম অঙ্ক এবং কোন এটিএমে প্রযোজ্য—এই শর্তগুলো একসঙ্গে পড়ুন। টাকা ও শতাংশ সরাসরি তুলনীয় নয়।','Read percentage charges, monetary floors and ATM conditions together. Taka amounts and percentages are not directly comparable.'),
 'foreign_currency_markup':('বিদেশে খরচ','Foreign spending','বিদেশি মুদ্রার লেনদেনের প্রকাশিত মার্কআপ। কোন মুদ্রায় প্রযোজ্য, তা ব্যাংকের শর্তে দেখুন।','The published foreign-currency markup. Check each bank’s currency conditions.'),
 'renewal_fee':('নবায়ন ফি','Renewal fee','কার্ড নবায়নের প্রকাশিত ফি। প্রথম বছরের বার্ষিক ফি থেকে এটি আলাদা হতে পারে।','The published renewal fee, which may differ from the first-year annual fee.')}

def build(result):
    attribute=result['choice']['attribute'];bn,en,meaning_bn,meaning_en=LABELS[attribute]
    title=display({'institution_id':'','column_header':'','network':result['choice']['network'] or '','tier':result['choice']['tier'] or ''})
    sections=[]
    def section(id,bn_heading,en_heading,paragraphs):
        if paragraphs:sections.append({'id':id,'heading_bn':bn_heading,'heading_en':en_heading,'paragraphs':paragraphs})
    fresh=[];old=[];missing=[];checking=[];unpublished=[]
    for bank in result['rows']:
        fact=bank.get('facts',{}).get(attribute)
        if not bank.get('card'):
            (checking if bank['state']=='checking' else unpublished).append(bank);continue
        if not fact:missing.append(bank);continue
        (old if fact['stale'] else fresh).append((bank,fact))
    def bankname(bank,language):return SHORT.get(bank['slug'],bank['name_bn']) if language=='bn' else EN_SHORT.get(bank['slug'],bank['name_en'].removesuffix(' PLC'))
    def value(fact,language):
        is_bn=language=='bn'
        if fact.get('value_num')==0 and fact['unit'] in {'bdt','text'}:return 'বিনামূল্যে' if is_bn else 'Free'
        if fact.get('value_num') is None:return to_bn_digits(fact['value_text']) if is_bn else fact['value_text']
        number=format_number(fact['value_num'],bn=is_bn)
        if fact['unit']=='bdt':return number+(' টাকা' if is_bn else ' BDT')
        if fact['unit']=='pct_year' or '%' in fact['value_text']:return number+'%'
        return number
    section('meaning',bn+' কী',en+' explained',[{'text_bn':meaning_bn,'text_en':meaning_en,'fact_ids':[]}])
    section('coverage','এই তুলনায় যে তথ্য আছে','Available information',[{'text_bn':f"{title['card_display_bn']} কার্ডের {bn} সম্পর্কে {format_number(len(fresh),bn=True)}টি ব্যাংকের পুরনো নয় এমন তথ্য আছে। নিচে প্রতিটি ব্যাংকের অঙ্ক, শর্ত ও তারিখ আলাদা অনুচ্ছেদে দেওয়া হলো।",'text_en':f"There are {len(fresh)} banks with non-stale {en.lower()} data for {title['card_display_en']}. Each bank’s amount, conditions and date are shown separately below.",'fact_ids':[]}])
    def paragraph(bank,fact):
        ids=[fact['offer_id']];texts={}
        for language in ['bn','en']:
            label=('বার্ষিক সুদের হার' if attribute=='interest_rate' else bn) if language=='bn' else ('annual interest rate' if attribute=='interest_rate' else en.lower())
            extra_condition=fact.get('condition_'+language,'')
            compound=attribute=='cash_advance_fee' and ('অথবা' in extra_condition or 'whichever is higher' in extra_condition)
            shown=extra_condition.rstrip('।.') if compound else value(fact,language)
            line=f"{GEN.get(bank['slug'],bankname(bank,language)+'-এর')} প্রকাশিত {label} {shown}।" if language=='bn' else f"{bankname(bank,language)}'s published {label} is {shown}."
            if extra_condition and not compound:
                if extra_condition in {'+১৫% ভ্যাট','+15% VAT'}:line+=(' এই ফির সঙ্গে ১৫% ভ্যাট যোগ হওয়ার শর্ত আছে।' if language=='bn' else ' This fee has a 15% VAT condition.')
                else:line+=' '+extra_condition.rstrip('।.')+('।' if language=='bn' else '.')
            if attribute=='cash_advance_fee' and re.search(r'at EBL ATM',fact.get('condition',''),re.I):line+=(' এটি ইস্টার্ন ব্যাংকের নিজস্ব এটিএমের জন্য প্রকাশিত শর্ত।' if language=='bn' else ' These published conditions are for an EBL ATM.')
            if attribute=='annual_fee':
                for key,prefix_bn,prefix_en in [('fee_waiver_rule','ফি মওকুফ','Fee waiver'),('renewal_fee','নবায়ন ফি','Renewal fee')]:
                    extra=bank['facts'].get(key)
                    if not extra or extra['stale']:continue
                    detail=extra.get('condition_'+language,'') if key=='fee_waiver_rule' else value(extra,language)
                    if detail:
                        line+=' '+((prefix_bn if language=='bn' else prefix_en)+': ' if key!='fee_waiver_rule' else '')+detail.rstrip('।.')+('।' if language=='bn' else '.')
                        if extra['doc_date']!=fact['doc_date']:line+=(' এই তথ্যের তারিখ: ' if language=='bn' else ' This condition’s date: ')+format_date(extra['doc_date'],bn=language=='bn')+('।' if language=='bn' else '.')
                        if extra['offer_id'] not in ids:ids.append(extra['offer_id'])
            line+=(' এই তালিকার তারিখ: ' if language=='bn' else ' Schedule date: ')+format_date(fact['doc_date'],bn=language=='bn')+('।' if language=='bn' else '.')
            if bank['status']['code']=='no_data':line+=(' এই ব্যাংকের আর্থিক অবস্থা যাচাই হয়নি।' if language=='bn' else ' This bank’s financial condition is unverified.')
            texts['text_'+language]=line
        return {**texts,'fact_ids':ids}
    section('published','ব্যাংকভিত্তিক তথ্য','Bank-by-bank information',[paragraph(bank,fact) for bank,fact in fresh])
    section('stale','পুরনো তথ্য—বর্তমান তুলনার বাইরে','Older information—outside the current comparison',[paragraph(bank,fact) for bank,fact in old])
    notes=[]
    for banks,text_bn,text_en in [(missing,'এই খরচের তথ্য নেই','No data for this cost'),(checking,'তথ্য যাচাই হচ্ছে','Data being checked'),(unpublished,'এই নেটওয়ার্ক ও স্তরের কার্ডের তথ্য প্রকাশিত নয়','No card published for this network and tier')]:
        if banks:notes.append({'text_bn':text_bn+': '+', '.join(bankname(bank,'bn') for bank in banks)+'।','text_en':text_en+': '+', '.join(bankname(bank,'en') for bank in banks)+'.','fact_ids':[]})
    notes.append({'text_bn':'এটি প্রকাশিত অঙ্ক ও শর্তের তুলনা, ব্যাংকের মানের র‌্যাঙ্কিং নয়। প্রতিটি অঙ্কের মূল সূত্র দেখে আবেদন করার আগে ব্যাংকের সাথে নিশ্চিত হোন।','text_en':'This compares published amounts and conditions, not bank quality. Check each source and confirm terms with the bank before applying.','fact_ids':[]})
    section('limits','তথ্যের সীমা ও শর্ত','Coverage and conditions',notes)
    return {'attribute':attribute,'title_bn':title['card_display_bn']+' · '+bn,'title_en':title['card_display_en']+' · '+en,'sections':sections}
