"""Well-known bank names outside the demo, used only to say "not in the demo yet".

These names carry no status, licence or financial claim. Names that overlap a
demo bank's aliases (for example other Islamic banks) are deliberately omitted.
"""
import re
from ilma_api.voice_text import normalize_alias

NAMES = [
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
]


def find_other_bank(text):
    """Return (name_bn, name_en) when the text names a listed non-demo bank."""
    tokens = normalize_alias(text).split()
    for name_bn, name_en, aliases in NAMES:
        for alias in aliases:
            words = normalize_alias(alias).split()
            # "ঢাকা ব্যাংক"/"one bank" normalize to one ordinary word, so "Dhaka"
            # or "one" alone never match: require "bank" directly after the name.
            if len(words) == 1 and len(alias.split()) > 1:
                if re.search(re.escape(alias.split()[0]) + r'\s*(?:ব্যাংক|bank)', text, re.I):
                    return name_bn, name_en
                continue
            if any(tokens[start:start + len(words)] == words for start in range(len(tokens))):
                return name_bn, name_en
    return None
