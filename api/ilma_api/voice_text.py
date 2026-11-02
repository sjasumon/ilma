"""APP_SPEC_02 transcript cleanup, language, numbers and conservative alias scoring."""
import re
import unicodedata
from functools import lru_cache
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from ilma_api.voice import VoiceError
from ilma_api.voice_agent import Conversation, Choice


class VoiceContext(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    tab: Literal['home', 'bank', 'services'] = 'home'
    bank_id: int | None = None
    ui_lang: Literal['bn', 'en'] = 'bn'
    history: list[dict[str, str]] = Field(default_factory=list, max_length=4)
    speak: bool = True
    agent: bool = False
    conversation: Conversation | None = None
    choice: Choice | None = None
    ivr_step: Literal['open', 'mic', 'language', 'menu', 'name', 'confirm', 'report', 'next'] | None = None
    audio_truncated: bool = False
    raw_text: str | None = None


class VoiceIntent(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    intent: Literal['bank_status', 'bank_detail', 'rates', 'service_compare', 'insurance', 'explain_word', 'out_of_scope', 'unclear']
    institution_ids: list[int] = Field(default_factory=list, max_length=4)
    product: Literal['fdr', 'dps', 'savings', 'credit_card', 'personal_loan', 'home_loan', 'car_loan', 'sme_loan', 'loan_against_fdr', 'account_fee'] | None = None
    card_tier: Literal['classic', 'gold', 'platinum', 'signature', 'world', 'infinite', 'titanium', 'blue', 'ultramarine'] | None = None
    service_attribute: Literal['annual_fee','renewal_fee','interest_rate','late_fee','foreign_currency_markup','cash_advance_fee','card_replacement_fee','supplementary_card_fee','maintenance_fee_half_yearly','sms_alert_fee','cheque_book_fee','closing_fee','atm_other_bank_fee','minimum_balance'] | None = None
    amount_bdt: int | None = Field(default=None, ge=0)
    period_months: int | None = Field(default=None, ge=1, le=600)


def clean_transcript(text):
    text = unicodedata.normalize('NFC', text).replace('जनता बैंक', 'জনতা ব্যাংক').replace('बैंक', 'ব্যাংক')
    # Danda/double danda are shared Bengali punctuation, despite occupying the
    # Devanagari Unicode block. Meta commonly ends valid Bangla with U+0964.
    if re.search('[\u0900-\u0963\u0966-\u097f]', text):
        raise VoiceError('unclear', 422, 'বুঝতে পারিনি। আবার বলুন বা লিখুন।', 'Not understood. Please speak again or type.')
    words = []
    for word in text.split():
        core = word.strip('.,?!:;।!"“”')
        if len(core) % 2 == 0 and len(core) >= 4 and core[:len(core)//2].casefold() == core[len(core)//2:].casefold():
            core = core[:len(core)//2]
            word = core
        if not words or words[-1].casefold().strip('.,?!:;।') != word.casefold().strip('.,?!:;।'):
            words.append(word)
    cleaned = ' '.join(words).strip()
    while cleaned and unicodedata.category(cleaned[-1]).startswith('P'): cleaned = cleaned[:-1].rstrip()
    return cleaned


def fold_bengali_vowels(value):
    # ASR spelling tolerance is only for matching; stored/source text stays intact.
    return unicodedata.normalize('NFC',value).translate(str.maketrans({'ূ':'ু','ী':'ি'}))


def normalize_alias(value):
    value = join_acronyms(value)
    value = fold_bengali_vowels(value).lower().translate(str.maketrans('০১২৩৪৫৬৭৮৯', '0123456789'))
    value = re.sub(r'ব্যাংক(?:ের|ে)?', ' ', value)
    value = re.sub(r'\b(bank|plc|ltd|limited)\b|পিএলসি|লিমিটেড', ' ', value)
    value = re.sub(r'[-–—]?এর(?=\s|$)|[-–—]?এর(?=[?!।])', ' ', value)
    value = ''.join(c if c.isalnum() or unicodedata.category(c).startswith('M') else ' ' for c in value)
    return ' '.join(value.split())


def join_acronyms(value):
    """Join only known spelled acronyms; never merge ordinary short words."""
    value=unicodedata.normalize('NFC',value)
    groups={'EBL':('ই বি এল','ইবিএল'),'MTB':('এম টি বি','এমটিবি'),
            'NCC':('এন সি সি','এনসিসি'),'DBBL':('ডি বি বি এল','ডিবিবিএল'),
            'SBAC':('এস বি এ সি','এসবিএসি'),'UCB':('ইউ সি বি','ইউসিবি')}
    for latin,(spelled,bangla) in groups.items():
        value=re.sub(r'(?<![A-Za-z])'+r'[\s.]*'.join(latin)+r'(?![A-Za-z])',latin,value,flags=re.I)
        value=re.sub(r'(?<![\w\u0980-\u09ff])'+r'[\s.]+'.join(map(re.escape,spelled.split()))+r'(?![\w\u0980-\u09ff])',bangla,value)
    return value


def related_parent_ids(text, banks):
    query=' '+normalize_alias(text)+' '
    return {bank['id'] for bank in banks if any(' '+normalize_alias(name)+' ' in query for name in bank.get('related_entities',[]))}


@lru_cache(maxsize=2048)
def indexed_alias(alias):
    normalized=normalize_alias(alias)
    return normalized,len(normalized.split())


def different_start(alias, heard):
    """A short Latin name must start alike: Sitty can be City, but Black cannot be SBAC."""
    same=lambda a,b:a==b or {a,b}=={'c','s'}
    return len(alias)<=5 and alias.isascii() and heard.isascii() and not same(alias[0],heard[0])


# Sound keys: a rough consonant skeleton so "Black", "Bragg", "ব্রেক" and "BRAC" sound alike.
BN_SOUNDS=str.maketrans({'ক':'k','খ':'k','গ':'k','ঘ':'k','চ':'c','ছ':'c','জ':'c','ঝ':'c','য':'c','ট':'t','ঠ':'t','ত':'t','থ':'t','ৎ':'t','ড':'t','ঢ':'t','দ':'t','ধ':'t','ন':'n','ণ':'n','প':'b','ফ':'f','ব':'b','ভ':'b','ম':'m','র':'r','ল':'r','শ':'s','ষ':'s','স':'s','হ':'','ং':'n','ঞ':'n','ঙ':'n',
 'অ':'a','আ':'a','ই':'a','ঈ':'a','উ':'a','ঊ':'a','এ':'a','ঐ':'a','ও':'a','ঔ':'a','ঋ':'a'})
COMMON_WORDS={'the','this','that','any','my','your','our','which','what','other','another','same','best','good','big','all','one','a','an','and','or','of','for','to','is','in','on','at','তার','এই','ওই','কোন','কোনো','সেই','আমার','আপনার','অন্য','ভালো','সব'}

def sound_key(word):
    """Consonant skeleton of one word; a leading vowel is kept as 'a'."""
    w=unicodedata.normalize('NFC',word.lower())
    if re.search(r'[\u0980-\u09ff]',w):
        w=w.replace('ঙ্গ','ং').replace('\u09cdয','').replace('ড\u09bc','র').replace('ঢ\u09bc','র').replace('য\u09bc','')
        w=''.join(ch for ch in w.translate(BN_SOUNDS) if ch.isascii());w=w[:1]+w[1:].replace('a','')
    else:
        if not w.isascii():return ''
        w=re.sub(r'ph','f',w);w=re.sub(r'ti(?=[aeiou])','s',w);w=re.sub(r'ng','n',w);w=re.sub(r'(?:ck|q)','k',w);w=re.sub(r'sh','s',w);w=re.sub(r'c(?=[eiy])','s',w);w=w.replace('c','k').replace('x','ks').replace('z','s')
        w=w.translate(str.maketrans({'g':'k','d':'t','p':'b','v':'b','l':'r','j':'c'}))
        lead='a' if w[:1] in 'aeiou' else ''
        w=lead+re.sub(r'[aeiouwhy]','',w)
    w=re.sub(r'(.)\1+',r'\1',re.sub(r'[^a-z]','',w))
    return w


def match_candidates(text, banks, scorer=None):
    query = normalize_alias(text)
    tokens = query.split()
    # The same words with "bank" kept, so a sound match can check the next word.
    raw_words=' '.join(''.join(c if c.isalnum() or unicodedata.category(c).startswith('M') else ' ' for c in fold_bengali_vowels(join_acronyms(text)).lower()).split()).split()
    raw_words=[w for w in raw_words if w not in {'plc','ltd','limited','পিএলসি','লিমিটেড'}]
    candidates = []
    matched_windows={}
    excluded=related_parent_ids(text,banks)
    for bank in banks:
        if bank['id'] in excluded:
            continue
        best, best_alias, best_window = 0, '', None
        for alias in [bank['name_bn'], bank['name_en'], *bank.get('aliases', [])]:
            normalized,width = indexed_alias(alias)
            if len(normalized) < 2 or normalized in {'bank', 'ব্যাংক', 'plc'}:
                continue
            # Sliding equal-size word windows avoid partial_ratio awarding 100 to
            # an acronym hidden inside a different long word.
            for start in range(len(tokens)):
                window = ' '.join(tokens[start:start + width])
                # Partial matches inside much longer words are not bank names.
                if min(len(window),len(normalized)) < max(len(window),len(normalized)) * .7:
                    continue
                if window == normalized:
                    score = 100
                elif len(normalized) <= 3:  # short acronyms must match exactly
                    score = 0
                else:
                    if scorer is None:
                        try:
                            from rapidfuzz.fuzz import partial_ratio
                            scorer = partial_ratio
                        except ImportError:
                            raise VoiceError('voice_dependency_missing', 503, 'ভয়েস সেবা প্রস্তুত নয়।', 'Install the voice service dependencies.') from None
                    score = 0 if different_start(normalized, window) else scorer(normalized, window)
                    # Partial substring alone is not sufficient for different-length words.
                    if score == 100 and len(window) != len(normalized):
                        score = 85
                if score > best:
                    best, best_alias, best_window = score, alias, (start,start+width)
        if best < 90:
            # A name that sounds the same, said right before "bank"/"ব্যাংক", is that bank ("Bragg Bank" is BRAC).
            for alias in [bank['name_bn'], bank['name_en'], *bank.get('aliases', [])]:
                normalized,width = indexed_alias(alias)
                if len(normalized)<4 or (normalized.isascii() and re.fullmatch(r'[a-z]{2,4}',normalized) and alias.strip().replace(' ','').isupper()):continue
                keys=[sound_key(w) for w in normalized.split()]
                if not all(len(k)>=2 for k in keys) or sum(map(len,keys))<3:continue
                for start in range(len(tokens)-width+1):
                    window=tokens[start:start+width]
                    if any(w in COMMON_WORDS for w in window) or [sound_key(w) for w in window]!=keys:continue
                    after=raw_words[start+width] if start+width<len(raw_words) else ''
                    if re.fullmatch(r'bank|ব্যাংক(?:ের|ে|টি|টা)?',after,re.I) and 90>best:
                        best,best_alias,best_window=90,alias,(start,start+width)
        if best >= 75:
            matched_windows[bank['id']]=best_window
            single = len(normalize_alias(best_alias).split()) == 1
            short_name = normalize_alias(best_alias) in {'prime', 'city', 'ncc', 'dhaka', 'national', 'break', 'black', 'brack', 'bragg', 'brak', 'ব্ল্যাক', 'ব্রাক', 'ন্যাশনাল', 'প্রাইম', 'সিটি', 'এনসিসি', 'ঢাকা'}
            follows = bool(re.search(re.escape(normalize_alias(best_alias)) + r'\s*(?:ব্যাংক|bank)', fold_bengali_vowels(text), re.I))
            candidates.append({**{k: bank[k] for k in ('id', 'slug', 'name_bn', 'name_en', 'type', 'coverage')},
                               'licensed': bank.get('licensed', True), 'confidence': round(best / 100, 3), 'alias': best_alias,
                               'confirm': bool(short_name and single and not follows)})
    # A full exact name outranks a shorter alias embedded inside it, such as
    # National inside National Credit and Commerce Bank. A separate occurrence
    # outside the full name still denotes a second bank and must be retained.
    def exact_spans(alias):
        words=normalize_alias(alias).split()
        return [(start,start+len(words)) for start in range(len(tokens)) if words and tokens[start:start+len(words)]==words]
    exact={row['id']:exact_spans(row['alias']) for row in candidates if row['confidence']==1}
    def embedded(row):
        spans=exact.get(row['id'],[])
        return bool(spans) and all(any(a<=start and end<=b and b-a>end-start for id,others in exact.items() if id!=row['id'] for a,b in others) for start,end in spans)
    candidates=[row for row in candidates if not embedded(row)]
    # Near matches entirely inside an exact name are spelling alternatives, not
    # a second named bank. Keep near matches occurring elsewhere in the query.
    def fuzzy_inside_exact(row):
        if row['confidence']==1:return False
        start,end=matched_windows[row['id']]
        return any(a<=start and end<=b for id,spans in exact.items() if id!=row['id'] for a,b in spans)
    candidates=[row for row in candidates if not fuzzy_inside_exact(row)]
    candidates.sort(key=lambda c: (-c['confidence'], c['id']))
    if not candidates:
        return []
    # Return close alternatives; never hide two banks explicitly named together.
    return [c for c in candidates if c['confidence'] >= max(.75, candidates[0]['confidence'] - .1)][:4]


def decide_language(text, candidates, ui_lang):
    remaining = normalize_alias(text)
    aliases = sorted({normalize_alias(c.get('alias','')) for c in candidates},key=len,reverse=True)
    # Remove whole matched alias phrases before counting language evidence.
    # A bare ASR bank name, including "break bank", must leave no English votes.
    for alias in aliases:
        if alias:remaining=re.sub(r'(?<!\S)'+re.escape(alias)+r'(?!\S)',' ',remaining,flags=re.I)
    remaining = re.sub(r'\b(bank|fdr|dps|rate|plc|card|loan)\b|ব্যাংক(?:ের|ে)?|পিএলসি', ' ', remaining, flags=re.I)
    letters = [c for c in remaining if c.isalpha()]
    latin = sum('LATIN' in unicodedata.name(c, '') for c in letters)
    if not letters:return ui_lang  # A bank name alone has no language evidence.
    return 'en' if latin / len(letters) >= .7 else 'bn'


from ilma_api.voice_numbers import normalize_numbers


def bank_name_only(text, candidates):
    remainder = normalize_alias(text)
    for candidate in candidates:
        remainder = remainder.replace(normalize_alias(candidate['alias']), ' ')
    return bool(candidates) and not remainder.strip()


def turn_language(text, context, candidates=(), choice=None):
    previous=context.conversation.language if context.conversation and context.conversation.language else context.ui_lang
    if choice is not None:return previous
    if context.conversation:
        from ilma_api.voice_agent import spoken_choice
        # Scripted replies follow the tap path, including its language.
        if spoken_choice(text,context.conversation) is not None:return previous
    return decide_language(text,candidates,previous)
