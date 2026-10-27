"""Number normalization and the Bangla speech lexicon (APP_SPEC_02 §5/6)."""
import re
from decimal import Decimal

BN_DIGITS = '০১২৩৪৫৬৭৮৯'
WORDS = ('শূন্য এক দুই তিন চার পাঁচ ছয় সাত আট নয় দশ এগারো বারো তেরো চৌদ্দ পনেরো ষোলো সতেরো আঠারো উনিশ '
'বিশ একুশ বাইশ তেইশ চব্বিশ পঁচিশ ছাব্বিশ সাতাশ আটাশ ঊনত্রিশ ত্রিশ একত্রিশ বত্রিশ তেত্রিশ চৌত্রিশ পঁয়ত্রিশ '
'ছত্রিশ সাঁইত্রিশ আটত্রিশ ঊনচল্লিশ চল্লিশ একচল্লিশ বিয়াল্লিশ তেতাল্লিশ চুয়াল্লিশ পঁয়তাল্লিশ ছেচল্লিশ সাতচল্লিশ '
'আটচল্লিশ ঊনপঞ্চাশ পঞ্চাশ একান্ন বাহান্ন তিপ্পান্ন চুয়ান্ন পঞ্চান্ন ছাপ্পান্ন সাতান্ন আটান্ন ঊনষাট ষাট একষট্টি '
'বাষট্টি তেষট্টি চৌষট্টি পঁয়ষট্টি ছেষট্টি সাতষট্টি আটষট্টি ঊনসত্তর সত্তর একাত্তর বাহাত্তর তিয়াত্তর চুয়াত্তর '
'পঁচাত্তর ছিয়াত্তর সাতাত্তর আটাত্তর ঊনআশি আশি একাশি বিরাশি তিরাশি চুরাশি পঁচাশি ছিয়াশি সাতাশি আটাশি '
'ঊননব্বই নব্বই একানব্বই বিরানব্বই তিরানব্বই চুরানব্বই পঁচানব্বই ছিয়ানব্বই সাতানব্বই আটানব্বই নিরানব্বই').split()
NUMBERS = {word: Decimal(index) for index, word in enumerate(WORDS)}
NUMBERS.update({'ছয়': Decimal(6), 'নয়': Decimal(9), 'দেড়': Decimal('1.5'), 'দেড়': Decimal('1.5'), 'আড়াই': Decimal('2.5')})
NUMBERS.update({word: Decimal(index) for index, word in enumerate('zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty'.split())})
NUMBER = r'(?:\d+(?:\.\d+)?|' + '|'.join(sorted(map(re.escape, NUMBERS), key=len, reverse=True)) + ')'
SCALES = {'কোটি': 10000000, 'crore': 10000000, 'লাখ': 100000, 'লক্ষ': 100000, 'lakh': 100000, 'হাজার': 1000, 'thousand': 1000, 'শত':100, 'hundred':100}
SCALE = '|'.join(map(re.escape, SCALES))


def numeric(token):
    return NUMBERS[token.lower()] if token.lower() in NUMBERS else Decimal(token)


def normalize_numbers(text):
    text = text.translate(str.maketrans(BN_DIGITS, '0123456789'))
    text = re.sub(r'(?<=\d),(?=\d)', '', text)
    def period(match):
        multiplier = 12 if match[2].lower() in {'বছর', 'year', 'years'} else 1
        value = numeric(match[1]) * multiplier
        rendered = format(value, 'f')
        if '.' in rendered: rendered = rendered.rstrip('0').rstrip('.')
        return rendered + ' months'
    text = re.sub(r'(?<!\w)(' + NUMBER + r')\s+(বছর|মাস|years?|months?)(?!\w)', period, text, flags=re.I)
    pairs = r'(?:' + NUMBER + r')\s+(?:' + SCALE + r')'
    def amount(match):
        total = sum((numeric(piece[1]) * SCALES[piece[2].lower()] for piece in re.finditer(r'(' + NUMBER + r')\s+(' + SCALE + r')', match[0], re.I)), Decimal(0))
        return f'{total:g} taka'
    return re.sub(r'(?<!\w)' + pairs + r'(?:\s+' + pairs + r')*(?!\w)', amount, text, flags=re.I)


def bangla_integer(number):
    if number < 0: return 'ঋণাত্মক ' + bangla_integer(-number)
    if number < 100: return WORDS[number]
    for divisor, suffix in [(10000000, 'কোটি'), (100000, 'লাখ'), (1000, 'হাজার'), (100, 'শত')]:
        if number >= divisor:
            quotient, remainder = divmod(number, divisor)
            return bangla_integer(quotient) + ' ' + suffix + (' ' + bangla_integer(remainder) if remainder else '')


def pronounce(text, language):
    text = re.sub(r'\b(?:PLC|Ltd)\.?\b|পিএলসি|লিমিটেড', '', text, flags=re.I)
    if language != 'bn': return text
    text = text.translate(str.maketrans(BN_DIGITS, '0123456789'))
    for before, after in [('22 অক্টোবর 2026', 'বাইশে অক্টোবর দুই হাজার ছাব্বিশ'), ('10.5%', 'সাড়ে দশ শতাংশ')]:
        text = text.replace(before, after)
    for before, after in [('FDR', 'এফডিআর'), ('DPS', 'ডিপিএস'), ('NBFI', 'আর্থিক প্রতিষ্ঠান')]:
        text = re.sub(r'\b' + before + r'\b', after, text, flags=re.I)
    def speak_number(match):
        value = match[0].replace(',', '')
        whole, dot, decimal = value.partition('.')
        words = bangla_integer(int(whole))
        return words + (' দশমিক ' + ' '.join(WORDS[int(digit)] for digit in decimal) if dot else '')
    text = re.sub(r'\d[\d,]*(?:\.\d+)?', speak_number, text)
    return text.replace('%', ' শতাংশ')
