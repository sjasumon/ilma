"""Short-lived server memory: signed opaque IDs, redacted user words, MySQL."""
from datetime import datetime,timedelta
import hashlib,hmac,re,secrets
from ilma_api import settings
from ilma_api.db import AppConversation


def redact_user(text):
    text=re.sub(r'(?:আমার নাম|my name is|my name\s*[:=])\s*[^।.!?\n]+','[name omitted]',text,flags=re.I)
    # Keep term/year questions; never retain a personal balance, PIN or account.
    text=re.sub(r'(?:[0-9০-৯][0-9০-৯,.]*|এক|দুই|তিন|চার|পাঁচ|দশ|one|two|three|five|ten)\s*(?:লাখ|লক্ষ|কোটি|হাজার|টাকা|lakh|crore|thousand|taka|BDT)(?:\s*(?:টাকা|taka))?','[personal amount omitted]',text,flags=re.I)
    text=re.sub(r'\b(?:password|otp)\b\s*[:#-]?\s*\S+|\b(?:account|pin)\b\s*(?:(?:no|number|nr|is|was)\b\.?\s*|[:#=-]\s*)*\S*[0-9০-৯]\S*|(?:পাসওয়ার্ড|ওটিপি)\s*[:#-]?\s*\S+|(?:পিন|অ্যাকাউন্ট নম্বর)\s*(?:(?:হলো|হল|নম্বর)\s*|[:#=-]\s*)*\S*[0-9০-৯]\S*','[identifier omitted]',text,flags=re.I)
    text=re.sub(r'[0-9০-৯][0-9০-৯ -]{6,}[0-9০-৯]','[identifier omitted]',text)
    return text[:1500]


def mask_identifiers(text):
    """For the "You said" line: hide a spoken PIN, account number, password or OTP, keep the other words."""
    text=re.sub(r'\b(?:password|otp)\b\s*[:#-]?\s*\S+|\b(?:account|pin)\b\s*(?:(?:no|number|nr|is|was)\b\.?\s*|[:#=-]\s*)*\S*[0-9০-৯]\S*|(?:পাসওয়ার্ড|ওটিপি)\s*[:#-]?\s*\S+|(?:পিন|অ্যাকাউন্ট নম্বর)\s*(?:(?:হলো|হল|নম্বর)\s*|[:#=-]\s*)*\S*[0-9০-৯]\S*','••••',text,flags=re.I)
    text=re.sub(r'[0-9০-৯][0-9০-৯ -]{6,}[0-9০-৯]','••••',text)
    return text


def redact_for_key(text):
    """Frozen copy of the older filter. Saved-answer question keys were made with it; never change it."""
    text=re.sub(r'(?:আমার নাম|my name is|my name\s*[:=])\s*[^।.!?\n]+','[name omitted]',text,flags=re.I)
    text=re.sub(r'(?:[0-9০-৯][0-9০-৯,.]*|এক|দুই|তিন|চার|পাঁচ|দশ|one|two|three|five|ten)\s*(?:লাখ|লক্ষ|কোটি|হাজার|টাকা|lakh|crore|thousand|taka|BDT)(?:\s*(?:টাকা|taka))?','[personal amount omitted]',text,flags=re.I)
    text=re.sub(r'\b(?:account|pin|password|otp)\b\s*[:#-]?\s*\S+|(?:পিন|অ্যাকাউন্ট নম্বর|পাসওয়ার্ড|ওটিপি)\s*[:#-]?\s*\S+','[identifier omitted]',text,flags=re.I)
    text=re.sub(r'[0-9০-৯][0-9০-৯ -]{6,}[0-9০-৯]','[identifier omitted]',text)
    return text[:1500]


def sign(id):return hmac.new(settings.VOICE_LOG_SALT.encode(),('conversation:'+id).encode(),hashlib.sha256).hexdigest()[:32]
def token(id):return id+'.'+sign(id)
def verified_id(value):
    if not value or not re.fullmatch(r'[a-f0-9]{32}\.[a-f0-9]{32}',value):return None
    id,signature=value.split('.')
    return id if hmac.compare_digest(signature,sign(id)) else None


def load(db,value=None):
    id=verified_id(value)
    row=db.get(AppConversation,id) if id else None
    if row and row.expires_at>datetime.utcnow():return id,row.memory
    return secrets.token_hex(16),{'last_turns':[],'spoken_fact_ids':[],'insurance_said':False}


def save(db,id,memory):
    now=datetime.utcnow();row=db.get(AppConversation,id)
    if row is None:row=AppConversation(conversation_id=id,created_at=now);db.add(row)
    row.memory=memory;row.updated_at=now;row.expires_at=now+timedelta(hours=24)
    db.flush()
