"""Bank awards as past facts. Code writes every award phrase; awards never explain condition."""
import re
from ilma_api.db import Awarder,BankAward,BankAwardSource

DISCLAIMER=('পুরস্কার ব্যাংকের নিরাপত্তার প্রমাণ নয়।','An award is not proof that a bank is safe.')
HIGH_RISK=('তবে পুরস্কার ব্যাংকের এখনকার অবস্থা বোঝায় না। আমাদের যাচাই করা তথ্যে এই ব্যাংকের ঝুঁকি বেশি।',
 'However, an award does not show the bank’s current condition. Our checked information shows this bank is high risk.')
MEDALS={'gold':('স্বর্ণ','gold'),'silver':('রৌপ্য','silver'),'bronze':('ব্রোঞ্জ','bronze')}
VERIFIED=('awarder_confirmed','independent_report')
DIGITS=str.maketrans('0123456789','০১২৩৪৫৬৭৮৯')


SPOKEN_AWARDER={'ifc':'আইএফসি'}
SPOKEN_AWARDER_EN={'ifc':'IFC','icsb':'ICSB'}
IFC_PURPOSE=(', বাণিজ্য অর্থায়নের জন্য',' for trade finance')
def rows(db,bank_id,confirmations=VERIFIED):
    query=db.query(BankAward,Awarder).join(Awarder,Awarder.awarder_id==BankAward.awarder_id).filter(
        BankAward.institution_id==bank_id,BankAward.award_year.isnot(None),BankAward.hide_in_app.is_(False),BankAward.paid_flag!='likely_paid',BankAward.confirmation.in_(confirmations))
    found=[]
    for award,awarder in query.all():
        sources=db.query(BankAwardSource).filter_by(award_id=award.award_id).all()
        sources.sort(key=lambda s:(s.source_kind!='awarder',s.source_kind!='news',s.id))
        found.append((award,awarder,sources))
    # Awarder-confirmed first, then the most recent year and announcement.
    found.sort(key=lambda r:(VERIFIED.index(r[0].confirmation),-(r[0].award_year or 0),-(r[0].announced_on.toordinal() if r[0].announced_on else 0),r[0].award_id))
    return found


LEADING=re.compile(r'best bank in [a-z]+$|বাংলাদেশের সেরা ব্যাংক',re.I)
def leading_first(found):
    """A best-bank-in-the-country award leads; category awards keep their newest-first order."""
    return sorted(found,key=lambda r:not LEADING.search(title(r[0].award_name_en)))


def intro_award(db,bank_id):
    """The one award an introduction may mention: awarder-confirmed and not likely paid."""
    found=leading_first(rows(db,bank_id,('awarder_confirmed',)))
    return found[0] if found else None


def title(name):
    name=name.split(':',1)[-1]
    name=re.sub(r'\s*\([^)]*\)','',name)
    return re.sub(r'\s*(?:[0-9০-৯]{4})\s*$','',name).strip()


def spoken_en(name):
    """"Best X, South Asia" reads as a title; speech says it as a phrase."""
    found=re.fullmatch(r'(.+?), (Trade Finance Mobilization), (South Asia)',name)
    if found:return f'an {found[1]} in {found[3]} for {found[2]}'
    return re.sub(r', (South Asia)$',r' in \1',name)


def medal_line(found,label,bn):
    """Medals from one awarder and category read as one sentence, newest first."""
    awards=[r[0] for r in found]
    if len(awards)<2 or not all(a.medal for a in awards) or len({(a.awarder_id,a.category.split(' - ')[-1]) for a in awards})!=1 or awards[0].awarder_id!='icsb':return None
    category=awards[0].category.split(' - ')[-1]
    if bn:
        said=' আর '.join(f"{str(a.award_year).translate(DIGITS)} সালে {MEDALS[a.medal][0]}" for a in awards)
        return f"{label} আইসিএসবি জাতীয় করপোরেট সুশাসন পুরস্কারে {title(awards[0].award_name_bn).split(' (')[0]} বিভাগে {said} পেয়েছে।"
    said=' and '.join(f"{MEDALS[a.medal][1]} in {a.award_year}" for a in awards)
    return f"{label} won {said} in the ICSB National Award for Corporate Governance Excellence, {category} category."


def phrase(award,awarder,language,subject=None):
    """One spoken sentence. With `subject` it starts with the bank's name."""
    bn=language=='bn';year=str(award.award_year)
    medal=MEDALS.get(award.medal)
    if bn:
        when=f"{year.translate(DIGITS)} সালে {SPOKEN_AWARDER.get(getattr(awarder,'awarder_id',''),awarder.name_bn)}";name=title(award.award_name_bn)
        # A word-for-word translation reads badly aloud; the pack's short name does not.
        if 'অসামান্য' in name and award.short_name_bn:name=award.short_name_bn
        start=f"{subject}কে {when}" if subject else f"{when} একে"
        if medal:return f"{start} {name} বিভাগে {medal[0]}পদক দিয়েছে।"
        if 'সম্মাননা' in name:return f"{start} {name} দিয়েছে।"
        if re.search(r'ব্যাংক|প্রতিষ্ঠান',name):return f"{start} {name} বলেছে{IFC_PURPOSE[0] if getattr(awarder,'awarder_id','')=='ifc' and 'বাণিজ্য' not in name else ''}।"
        return f"{start} {name} পুরস্কার দিয়েছে।"
    name=spoken_en(title(award.award_name_en));giver=SPOKEN_AWARDER_EN.get(getattr(awarder,'awarder_id',''),awarder.name)
    if subject:
        if medal:return f"{subject} won {medal[1]} in {giver}’s {name} category in {year}."
        if re.search(r'\bbank|institution',name,re.I):return f"{subject} was named {name} by {giver} in {year}."
        return f"{subject} received the {name} award from {giver} in {year}."
    if medal:return f"In {year}, {giver} gave it {medal[1]} in {name}."
    if re.search(r'\bbank|institution',name,re.I):return f"In {year}, {giver} named it {name}."
    return f"In {year}, {giver} gave it the {name} award."


def fact(award,awarder,sources,language):
    """Card line under recognition; the paid flag is never shown."""
    bn=language=='bn';source=sources[0] if sources else None
    text_bn=f"স্বীকৃতি: {award.award_name_bn} — {awarder.name_bn}, {str(award.award_year).translate(DIGITS)}। {DISCLAIMER[0]}"
    text_en=f"Recognition: {award.award_name_en} — {awarder.name}, {award.award_year}. {DISCLAIMER[1]}"
    return {'fact_id':'award:'+award.award_id,'institution_id':award.institution_id,'kind':'award','text_bn':text_bn,'text_en':text_en,
        'values':{'award_year':award.award_year,'confirmation':award.confirmation},
        'source':{'source_url':source.url if source else '','source_title':(source.outlet if source else awarder.name) or awarder.name,
            'quote':source.quote if source else '','published_at':str(source.published_on) if source and source.published_on else ''}}
