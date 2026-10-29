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
            return (WORDS[quotient] + 'শো' if divisor == 100 else bangla_integer(quotient) + ' ' + suffix) + (' ' + bangla_integer(remainder) if remainder else '')


def bangla_number(value, *, ratio=False):
    """Lakh/crore words; ratios round to whole positive or tenths negative."""
    from decimal import ROUND_HALF_UP
    number=Decimal(str(value));negative=number<0;number=abs(number)
    if ratio:
        quantum=Decimal(1).scaleb(number.adjusted()) if 0<number<Decimal('.1') else Decimal('.1') if negative else Decimal('1')
        number=number.quantize(quantum,rounding=ROUND_HALF_UP)
    whole=int(number);fraction=number-whole
    if fraction==Decimal('.25') and whole>=1:words='সোয়া '+bangla_integer(whole)
    elif fraction==Decimal('.5'):
        words='অর্ধেক' if whole==0 else 'দেড়' if whole==1 else 'আড়াই' if whole==2 else 'সাড়ে '+bangla_integer(whole)
    elif fraction==Decimal('.75'):words='পৌনে '+bangla_integer(whole+1)
    else:
        decimal=format(number,'f').partition('.')[2].rstrip('0')
        words=bangla_integer(whole)+(' দশমিক '+' '.join(WORDS[int(d)] for d in decimal) if decimal else '')
    return ('মাইনাস ' if negative else '')+words


BN_LEXICON={'AAA':'ট্রিপল এ','CRAB':'ক্র্যাব','CRISL':'ক্রিসল','ECRL':'ই সি আর এল',
 'FDR':'এফডিআর','DPS':'ডিপিএস','NBFI':'আর্থিক প্রতিষ্ঠান','BRAC':'ব্র্যাক','DBBL':'ডাচ বাংলা',
 'NCC':'এন সি সি','MTB':'এম টি বি','SBAC':'সাউথ বাংলা','EBL':'ইস্টার্ন ব্যাংক',
 'NPL':'খেলাপি ঋণ','CRAR':'মূলধনের অনুপাত','AA':'ডাবল এ','A':'এ','B':'বি','C':'সি',
 'PLC':'','Ltd':'','Limited':''}
LATIN_LETTERS=dict(zip('ABCDEFGHIJKLMNOPQRSTUVWXYZ',('এ বি সি ডি ই এফ জি এইচ আই জে কে এল এম এন ও পি কিউ আর এস টি ইউ ভি ডাবলিউ এক্স ওয়াই জেড').split()))


def pronounce(text, language):
    """Idempotent TTS-only normalization; the displayed speech keeps its digits."""
    text=re.sub(r'\b(?:PLC|Ltd|Limited)\b\.?|পিএলসি|লিমিটেড','',text,flags=re.I)
    text=text.translate(str.maketrans(BN_DIGITS,'0123456789')).replace('−','-')
    text=re.sub(r'[()\[\]·—–;]',', ',text)
    if language!='bn':
        text=re.sub(r'\bAAA\b','triple A',text)
        text=re.sub(r'\bTk\.?\s*([\d,]+(?:\.\d+)?)',r'\1 taka',text,flags=re.I)
        return ' '.join(text.replace('%',' percent').split())
    text=text.replace('22 অক্টোবর 2026','বাইশে অক্টোবর দুই হাজার ছাব্বিশ')
    for before,after in BN_LEXICON.items():
        text=re.sub(r'(?<![A-Za-z])'+re.escape(before)+r'(?![A-Za-z])',after,text,flags=re.I)
    # Unknown Latin words are spelled, never silently removed from a source name.
    text=re.sub(r'[A-Za-z]+',lambda m:' '.join(LATIN_LETTERS[c] for c in m[0].upper()),text)
    text=re.sub(r'-([0-9,]+(?:\.[0-9]+)?)\s*%',lambda m:bangla_number('-'+m[1].replace(',',''),ratio=True)+' শতাংশ',text)
    def speak_number(match):
        return bangla_number(match[0].replace(',',''))
    text=re.sub(r'-?\d[\d,]*(?:\.\d+)?',speak_number,text)
    return ' '.join(text.replace('%',' শতাংশ').split())
