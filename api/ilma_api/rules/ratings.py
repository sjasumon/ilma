import re
import logging

logger = logging.getLogger(__name__)

SCALE = [
    "AAA", "AA+", "AA", "AA-", "A+", "A", "A-",
    "BBB+", "BBB", "BBB-", "BB+", "BB", "BB-",
    "B+", "B", "B-", "CCC+", "CCC", "CCC-", "CC", "C", "D"
]

SCALE_INDEX = {g: i for i, g in enumerate(SCALE)}

CRAB_MAP = {
    "AA1": "AA+", "AA2": "AA", "AA3": "AA-",
    "A1": "A+", "A2": "A", "A3": "A-",
    "BBB1": "BBB+", "BBB2": "BBB", "BBB3": "BBB-",
    "BB1": "BB+", "BB2": "BB", "BB3": "BB-",
    "B1": "B+", "B2": "B", "B3": "B-"
}

def normalize_rating(grade: str) -> str | None:
    if not grade:
        return None
    cleaned = grade.strip()
    cleaned = re.sub(r'\(.*?\)', '', cleaned).strip()
    cleaned = cleaned.replace(" ", "")
    
    if cleaned in CRAB_MAP:
        cleaned = CRAB_MAP[cleaned]
    
    if cleaned in SCALE_INDEX:
        return cleaned
    
    logger.warning("Unrecognized credit rating grade: %s", grade)
    return None

def is_at_or_below(grade: str, threshold_grade: str) -> bool:
    norm_grade = normalize_rating(grade)
    norm_thresh = normalize_rating(threshold_grade)
    if not norm_grade or not norm_thresh:
        return False
    return SCALE_INDEX[norm_grade] >= SCALE_INDEX[norm_thresh]

def is_at_or_above(grade: str, threshold_grade: str) -> bool:
    norm_grade = normalize_rating(grade)
    norm_thresh = normalize_rating(threshold_grade)
    if not norm_grade or not norm_thresh:
        return False
    return SCALE_INDEX[norm_grade] <= SCALE_INDEX[norm_thresh]
