"""Well-known bank names outside the demo, used only to say "not in the demo yet".

These names carry no status, licence or financial claim. Names that overlap a
demo bank's aliases (for example other Islamic banks) are deliberately omitted.
"""
import re
from ilma_api.voice_text import normalize_alias

NAMES = [
    ('সিটিব্যাংক এনএ', 'Citibank N.A.', ['citibank n a','citi bank n a','সিটিব্যাংক এনএ']),
    ('পূবালী ব্যাংক', 'Pubali Bank', ['পূবালী', 'পুবালী', 'পূবালি', 'pubali']),
    ('সোনালী ব্যাংক', 'Sonali Bank', ['সোনালী', 'সোনালি', 'sonali']),
    ('জনতা ব্যাংক', 'Janata Bank', ['জনতা', 'janata']),
    ('অগ্রণী ব্যাংক', 'Agrani Bank', ['অগ্রণী', 'অগ্রনী', 'agrani']),
    ('রূপালী ব্যাংক', 'Rupali Bank', ['রূপালী', 'রুপালী', 'rupali']),
    ('উত্তরা ব্যাংক', 'Uttara Bank', ['উত্তরা', 'uttara']),
    ('ইউনাইটেড কমার্শিয়াল ব্যাংক', 'United Commercial Bank', ['ইউনাইটেড কমার্শিয়াল', 'ইউসিবি', 'united commercial', 'ucb']),
    ('ঢাকা ব্যাংক', 'Dhaka Bank', ['ঢাকা ব্যাংক', 'dhaka bank']),
    ('ওয়ান ব্যাংক', 'ONE Bank', ['ওয়ান ব্যাংক', 'one bank']),
    ('যমুনা ব্যাংক', 'Jamuna Bank', ['যমুনা', 'jamuna']),
    ('সাউথইস্ট ব্যাংক', 'Southeast Bank', ['সাউথইস্ট', 'southeast']),
    ('মার্কেন্টাইল ব্যাংক', 'Mercantile Bank', ['মার্কেন্টাইল', 'mercantile']),
    ('এক্সিম ব্যাংক', 'EXIM Bank', ['এক্সিম', 'exim']),
    ('স্ট্যান্ডার্ড চার্টার্ড', 'Standard Chartered', ['স্ট্যান্ডার্ড চার্টার্ড', 'standard chartered']),
    ('আইএফআইসি ব্যাংক', 'IFIC Bank', ['আইএফআইসি', 'ific']),
    ('বাংলাদেশ কৃষি ব্যাংক', 'Bangladesh Krishi Bank', ['কৃষি ব্যাংক', 'krishi bank', 'বিকেবি', 'bkb']),
    # Real banks whose names contain one of ours: never answer them with our bank's figures.
    ('শাহজালাল ইসলামী ব্যাংক', 'Shahjalal Islami Bank', ['শাহজালাল', 'shahjalal', 'sjibl']),
    ('আল-আরাফাহ ইসলামী ব্যাংক', 'Al-Arafah Islami Bank', ['আল আরাফাহ', 'আল-আরাফাহ', 'আরাফাহ', 'al arafah', 'al-arafah', 'arafah', 'aibl']),
    ('সোশ্যাল ইসলামী ব্যাংক', 'Social Islami Bank', ['সোশ্যাল ইসলামী', 'সোশ্যাল ইসলামি', 'social islami', 'sibl']),
    ('ফার্স্ট সিকিউরিটি ইসলামী ব্যাংক', 'First Security Islami Bank', ['ফার্স্ট সিকিউরিটি', 'first security', 'fsibl']),
    ('গ্লোবাল ইসলামী ব্যাংক', 'Global Islami Bank', ['গ্লোবাল ইসলামী', 'global islami']),
    ('ইউনিয়ন ব্যাংক', 'Union Bank', ['ইউনিয়ন ব্যাংক', 'union bank']),
    ('স্ট্যান্ডার্ড ব্যাংক', 'Standard Bank', ['স্ট্যান্ডার্ড ব্যাংক', 'standard bank']),
    ('প্রিমিয়ার ব্যাংক', 'Premier Bank', ['প্রিমিয়ার', 'premier']),
    ('ট্রাস্ট ব্যাংক', 'Trust Bank', ['ট্রাস্ট ব্যাংক', 'trust bank']),
    ('ব্যাংক আলফালাহ', 'Bank Alfalah', ['আলফালাহ', 'alfalah']),
    ('কমিউনিটি ব্যাংক', 'Community Bank', ['কমিউনিটি ব্যাংক', 'community bank']),
    ('মেঘনা ব্যাংক', 'Meghna Bank', ['মেঘনা', 'meghna']),
    ('মধুমতি ব্যাংক', 'Modhumoti Bank', ['মধুমতি', 'modhumoti']),
    ('এনআরবি ব্যাংক', 'NRB Bank', ['এনআরবি ব্যাংক', 'nrb bank', 'এনআরবিসি', 'nrbc']),
    ('বেসিক ব্যাংক', 'BASIC Bank', ['বেসিক ব্যাংক', 'basic bank']),
]
CENTRAL=re.compile(r'(?<!ইসলামী )(?<!ইসলামি )বাংলাদেশ ব্যাংক(?!\s*(?:পিএলসি|লিমিটেড))|(?<!islami )\bbangladesh bank\b(?!\s*(?:plc|ltd|limited))|কেন্দ্রীয় ব্যাংক|\bcentral bank\b',re.I)
# "Trust Bank" is not "Mutual Trust Bank"; "Union Bank" is not inside another name.
NOT_AFTER={'trust bank':r'mutual\s+','ট্রাস্ট ব্যাংক':r'মিউচুয়াল\s+'}


def is_central_bank(text):
    return bool(CENTRAL.search(text))


def find_other_bank(text):
    """Return (name_bn, name_en) when the text names a listed non-demo bank."""
    tokens = normalize_alias(text).split()
    for name_bn, name_en, aliases in NAMES:
        for alias in aliases:
            words = normalize_alias(alias).split()
            # "ঢাকা ব্যাংক"/"one bank" normalize to one ordinary word, so "Dhaka"
            # or "one" alone never match: require "bank" directly after the name.
            if len(words) == 1 and len(alias.split()) > 1:
                before=NOT_AFTER.get(alias.lower())
                if re.search((r'(?<!\S)' if not before else '')+re.escape(alias.split()[0]) + r'\s*(?:ব্যাংক|bank)', text, re.I) and not (before and re.search(before+re.escape(alias.split()[0]),text,re.I)):
                    return name_bn, name_en
                continue
            if any(tokens[start:start + len(words)] == words for start in range(len(tokens))):
                return name_bn, name_en
    return None
