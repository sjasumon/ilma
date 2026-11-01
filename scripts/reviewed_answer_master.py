"""Select the explicitly requested Bangla reference section without proposal fallback."""
import re

MASTER_SECTION='Current/reference full answer — Bangla'
LEGACY_CLOSING='এফডিআর বা ডিপিএসের সুদ শুনবেন?'

def reference_bangla(document,expected_count=93):
    sections=re.findall(r'^## Q(\d+)\.[^\n]*\n(.*?)(?=^## Q\d+\.|\Z)',document,re.M|re.S)
    ids=[int(number) for number,_ in sections]
    if len(ids)!=expected_count or set(ids)!=set(range(1,expected_count+1)):raise ValueError('Incomplete or duplicate reference questions')
    rows={}
    for number,body in sections:
        pattern=r'^\*\*'+re.escape(MASTER_SECTION)+r'\*\*[ \t]*\n\n(.*?)(?=\n\n\*\*|\Z)'
        matches=re.findall(pattern,body,re.M|re.S)
        if len(matches)!=1 or not matches[0].strip():raise ValueError('Missing or duplicate Bangla reference answer')
        text=matches[0].strip()
        # This is the owner's one explicit wording exception, not a general closing rewrite.
        text=text.replace(LEGACY_CLOSING,'').strip()
        if not text:raise ValueError('Empty reference answer')
        rows[int(number)]=text
    return rows
