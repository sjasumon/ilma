"""Exact guided-mode commands; never intercept a bank or a financial question."""
import re
import unicodedata

COMMANDS = {
    'again': ('আবার', 'again'), 'reasons': ('কারণ', 'reasons'),
    'insurance': ('বীমা', 'insurance'), 'sources': ('উৎস', 'সূত্র', 'source', 'sources'),
    'name': ('নতুন ব্যাংক', 'new bank'), 'stop': ('থামুন', 'stop'),
    'one': ('হ্যাঁ', 'হ্যা', 'yes', 'এক', 'একবার', 'one', '1', '১'),
    'two': ('না', 'no', 'দুই', 'দুইবার', 'two', '2', '২'),
    'bn': ('বাংলা', 'bangla', 'bengali'), 'en': ('ইংরেজি', 'english'),
}

def match_ivr_action(text, step):
    if not step:
        return None
    value = unicodedata.normalize('NFC', text).casefold().strip()
    value = re.sub(r'[।.!?,:;]+$', '', value).strip()
    value = ' '.join(value.split())
    for action, phrases in COMMANDS.items():
        if value in phrases:
            if action in {'bn', 'en'} and step != 'language':
                return None
            return action
    return None
