from datetime import date
from decimal import Decimal

BN_DIGITS = str.maketrans("0123456789.", "০১২৩৪৫৬৭৮৯.")

MONTHS_BN = {
    1: "জানুয়ারি", 2: "ফেব্রুয়ারি", 3: "মার্চ", 4: "এপ্রিল",
    5: "মে", 6: "জুন", 7: "জুলাই", 8: "আগস্ট",
    9: "সেপ্টেম্বর", 10: "অক্টোবর", 11: "নভেম্বর", 12: "ডিসেম্বর"
}

MONTHS_EN = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
}

def to_bn_digits(val: str | int | float) -> str:
    return str(val).translate(BN_DIGITS)

def format_percent(ratio: float | Decimal, bn: bool = False) -> str:
    pct = float(ratio) * 100.0
    text = f"{pct:.2f}".rstrip("0").rstrip(".")
    if bn:
        return to_bn_digits(text)
    return text

def format_crore(taka: int | float | Decimal, bn: bool = False) -> str:
    crore = abs(float(taka)) / 10_000_000.0
    text = f"{crore:.2f}".rstrip("0").rstrip(".")
    if bn:
        return to_bn_digits(text)
    return text

def format_date(d: date | str, bn: bool = False) -> str:
    if isinstance(d, str):
        try:
            d = date.fromisoformat(d)
        except Exception:
            return to_bn_digits(d) if bn else d
    if bn:
        return f"{to_bn_digits(d.day)} {MONTHS_BN.get(d.month, '')} {to_bn_digits(d.year)}"
    return f"{d.day} {MONTHS_EN.get(d.month, '')} {d.year}"

FORBIDDEN_WORDS = ["দেউলিয়া", "ডুবে যাচ্ছে"]

def check_forbidden_words(text: str) -> None:
    for word in FORBIDDEN_WORDS:
        if word in text:
            raise ValueError(f"Forbidden word '{word}' found in reason text: {text}")
