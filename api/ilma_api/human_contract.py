"""Structured understanding/wording and allowed UI actions."""
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field

Intent=Literal['bank_overview','bank_condition','bank_reasons','bank_figures','bank_history','bank_profile','services_list','service_detail','compare','insurance','explain_term','advice_request','best_bank','repeat','correction','smalltalk','stop','out_of_scope','unclear']
Button=Literal['detail','services','figures','history','fdr','dps','card','home_loan','compare','ask_bank','end','repeat','more','yes','no','confirm_bank','reject_bank','bank_1','bank_2','bank_3','listen']
class BankResolution(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:int|None
    source:Literal['conversation','named','asked']
    mention:str|None=Field(max_length=160)
class HumanReply(BaseModel):
    model_config=ConfigDict(extra='forbid')
    intent:Intent
    bank:BankResolution
    product:Literal['fdr','dps','savings','card','home_loan','auto_loan','personal_loan','loan_against_fdr','account_fee']|None
    basis:Literal['conventional','islamic']|None
    tenor_months:int|None=Field(ge=1,le=600)
    network:Literal['Visa','Mastercard','Amex']|None
    tier:Literal['Classic','Gold','Platinum','Signature','World','Infinite','Titanium']|None
    compare_banks:list[int]=Field(max_length=4)
    needs_facts:Literal['bank','product','compare','profile','history','term']|None
    used_fact_ids:list[str]=Field(max_length=12)
    reply:str=Field(max_length=3000)
    sentence_fact_ids:list[list[str]]=Field(max_length=8)
    next_question:str=Field(max_length=200)
    buttons:list[Button]=Field(max_length=2)
    language:Literal['bn','en']

STATE={'bank_overview':'BANK','bank_condition':'BANK','bank_reasons':'DETAIL','bank_figures':'FIGURES','bank_history':'HISTORY','bank_profile':'DETAIL','services_list':'SERVICES','service_detail':'SERVICE','compare':'COMPARE','insurance':'NEXT','explain_term':'DETAIL','advice_request':'SERVICES','best_bank':'SERVICES','smalltalk':'ASK_BANK','stop':'NEXT','out_of_scope':'ASK_BANK','unclear':'ASK_BANK','correction':'BANK','repeat':'BANK'}
LABELS={
 'listen':('আবার বলুন','Ask again'),
 'detail':('আরও বিস্তারিত','More details'),'services':('ব্যাংকের সেবা','Bank services'),'figures':('আর্থিক হিসাব','Financial figures'),'history':('আগের ঘটনা','Past events'),
 'fdr':('এফডিআর','FDR'),'dps':('ডিপিএস','DPS'),'card':('কার্ড','Card'),'home_loan':('গৃহঋণ','Home loan'),
 'compare':('মিলিয়ে দেখুন','Compare'),'ask_bank':('অন্য ব্যাংক','Another bank'),'end':('শেষ','Finish'),'repeat':('আবার শুনুন','Listen again'),'more':('আরও শুনুন','Hear more'),
 'yes':('হ্যাঁ','Yes'),'no':('না','No'),'confirm_bank':('হ্যাঁ','Yes'),'reject_bank':('না','No')}
ALLOWED={
 'BANK':{'detail','services','history','figures','ask_bank','fdr','dps'},'DETAIL':{'figures','history','services','ask_bank','fdr','dps'},'FIGURES':{'services','history','ask_bank','fdr','dps'},
 'HISTORY':{'services','detail','ask_bank','fdr','dps'},'SERVICES':{'fdr','dps','card','home_loan','ask_bank'},'SERVICE':{'compare','services','ask_bank'},
 'COMPARE':{'bank_1','bank_2','bank_3','services','ask_bank'},'NEXT':{'services','ask_bank','end'},'ASK_BANK':{'ask_bank','end','fdr','dps','listen'},'WATCH_CONFIRM':{'yes','no'}}
