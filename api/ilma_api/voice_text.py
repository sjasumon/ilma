"""APP_SPEC_02 transcript cleanup, language, numbers and conservative alias scoring."""
import re
import unicodedata
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from ilma_api.voice import VoiceError


class VoiceContext(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    tab: Literal['home', 'bank', 'services'] = 'home'
    bank_id: int | None = None
    ui_lang: Literal['bn', 'en'] = 'bn'
    history: list[dict[str, str]] = Field(default_factory=list, max_length=3)
    speak: bool = True


class VoiceIntent(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    intent: Literal['bank_status', 'bank_detail', 'rates', 'service_compare', 'insurance', 'explain_word', 'out_of_scope', 'unclear']
    institution_ids: list[int] = Field(default_factory=list, max_length=4)
    product: Literal['fdr', 'dps', 'savings', 'credit_card', 'personal_loan', 'home_loan', 'car_loan', 'sme_loan'] | None = None
    card_tier: Literal['classic', 'gold', 'platinum', 'signature'] | None = None
    amount_bdt: int | None = Field(default=None, ge=0)
    period_months: int | None = Field(default=None, ge=1, le=600)


def clean_transcript(text):
    text = unicodedata.normalize('NFC', text).replace('जनता बैंक', 'জনতা ব্যাংক').replace('बैंक', 'ব্যাংক')
    if re.search('[\u0900-\u097f]', text):
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


def normalize_alias(value):
    value = unicodedata.normalize('NFC', value).lower().translate(str.maketrans('০১২৩৪৫৬৭৮৯', '0123456789'))
    value = re.sub(r'ব্যাংক(?:ের|ে)?', ' ', value)
    value = re.sub(r'\b(bank|plc|ltd|limited)\b|পিএলসি|লিমিটেড', ' ', value)
    value = re.sub(r'[-–—]?এর(?=\s|$)|[-–—]?এর(?=[?!।])', ' ', value)
    value = ''.join(c if c.isalnum() or unicodedata.category(c).startswith('M') else ' ' for c in value)
    return ' '.join(value.split())


def match_candidates(text, banks, scorer=None):
    query = normalize_alias(text)
    tokens = query.split()
    candidates = []
    for bank in banks:
        best, best_alias = 0, ''
        for alias in [bank['name_bn'], bank['name_en'], *bank.get('aliases', [])]:
            normalized = normalize_alias(alias)
            if len(normalized) < 2 or normalized in {'bank', 'ব্যাংক', 'plc'}:
                continue
            # Sliding equal-size word windows avoid partial_ratio awarding 100 to
            # an acronym hidden inside a different long word.
            width = len(normalized.split())
            for start in range(len(tokens)):
                window = ' '.join(tokens[start:start + width])
                if len(window) < len(normalized) * .7:
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
                    score = scorer(normalized, window)
                    # Partial substring alone is not sufficient for different-length words.
                    if score == 100 and len(window) != len(normalized):
                        score = 85
                if score > best:
                    best, best_alias = score, alias
        if best >= 75:
            single = len(normalize_alias(best_alias).split()) == 1
            short_name = normalize_alias(best_alias) in {'prime', 'city', 'ncc', 'dhaka', 'প্রাইম', 'সিটি', 'এনসিসি', 'ঢাকা'}
            follows = bool(re.search(re.escape(normalize_alias(best_alias)) + r'\s*(?:ব্যাংক|bank)', text, re.I))
            candidates.append({**{k: bank[k] for k in ('id', 'slug', 'name_bn', 'name_en', 'type', 'coverage')},
                               'licensed': bank.get('licensed', True), 'confidence': round(best / 100, 3), 'alias': best_alias,
                               'confirm': bool(short_name and single and not follows)})
    candidates.sort(key=lambda c: (-c['confidence'], c['id']))
    if not candidates:
        return []
    # Return close alternatives; never hide two banks explicitly named together.
    return [c for c in candidates if c['confidence'] >= max(.75, candidates[0]['confidence'] - .1)][:4]


def decide_language(text, candidates, ui_lang):
    remaining = normalize_alias(text)
    aliases = sorted({c.get('alias', '') for c in candidates}, key=len, reverse=True)
    for alias in aliases:
        if alias:
            remaining = re.sub(re.escape(normalize_alias(alias)), ' ', remaining, flags=re.I)
    remaining = re.sub(r'\b(bank|fdr|dps|rate|plc|card|loan)\b|ব্যাংক(?:ের|ে)?|পিএলসি', ' ', remaining, flags=re.I)
    letters = [c for c in remaining if c.isalpha()]
    latin = sum('LATIN' in unicodedata.name(c, '') for c in letters)
    return 'en' if letters and latin / len(letters) >= .7 else ui_lang


from ilma_api.voice_numbers import normalize_numbers


def bank_name_only(text, candidates):
    remainder = normalize_alias(text)
    for candidate in candidates:
        remainder = remainder.replace(normalize_alias(candidate['alias']), ' ')
    return bool(candidates) and not remainder.strip()
