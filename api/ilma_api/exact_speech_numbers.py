"""Lossless TTS number spelling; display text and financial precision are untouched."""
import re
from ilma_api.voice_numbers import BN_DIGITS,bangla_integer

NUMBER=re.compile(r'-?(?:\d{1,3}(?:,\d{2})*,\d{3}|\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?')
SMALL='zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split()
TENS={20:'twenty',30:'thirty',40:'forty',50:'fifty',60:'sixty',70:'seventy',80:'eighty',90:'ninety'}

def english_integer(value):
    if value<20:return SMALL[value]
    if value<100:
        q,r=divmod(value,10);return TENS[q*10]+('-'+SMALL[r] if r else '')
    for scale,word in [(10**12,'trillion'),(10**9,'billion'),(10**6,'million'),(1000,'thousand'),(100,'hundred')]:
        if value>=scale:
            q,r=divmod(value,scale);return english_integer(q)+' '+word+(' '+english_integer(r) if r else '')

def number_words(token,language):
    token=token.replace(',','');negative=token.startswith('-');token=token.lstrip('-');whole,sep,fraction=token.partition('.')
    integer=bangla_integer if language=='bn' else english_integer
    words=integer(int(whole))
    if sep:words+=(' দশমিক ' if language=='bn' else ' point ')+' '.join(integer(int(d)) for d in fraction)
    return ('মাইনাস ' if language=='bn' else 'minus ') + words if negative else words

def prepare(text,language):
    """Return a speech-only script and an auditable exact number-to-word map."""
    if language not in {'bn','en'}:raise ValueError('Unsupported speech language')
    rendered=text.translate(str.maketrans(BN_DIGITS,'0123456789')).replace('−','-')
    rendered=re.sub(r'(?<=\d)[–—-](?=\d)',' থেকে ' if language=='bn' else ' to ',rendered)
    rendered=re.sub(r'(?:মাইনাস|ঋণাত্মক|minus)\s+(?=\d)','-',rendered,flags=re.I)
    if language=='en':
        # Say currency after the amount while preserving explicit lakh/crore units.
        rendered=re.sub(r'\bTk\.?\s*('+NUMBER.pattern+r')(?:\s+(lakh|crore|thousand|million|billion))?',lambda m:m[1]+(' '+m[2] if m[2] else '')+' taka',rendered,flags=re.I)
    spans=[]
    def replace(match):
        spoken=number_words(match[0],language);spans.append(dict(value=match[0].replace(',',''),spoken=spoken));return spoken
    rendered=NUMBER.sub(replace,rendered).replace('%',' শতাংশ' if language=='bn' else ' percent')
    rendered=' '.join(rendered.split())
    if re.search(r'[0-9০-৯%]',rendered):raise ValueError('Unconverted speech number')
    return rendered,spans
