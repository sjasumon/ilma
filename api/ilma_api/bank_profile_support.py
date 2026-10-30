"""Supplementary reviewed profile references and reproducible bank comparisons."""
from ilma_api.db import Fact,Institution
BANKS={'bankasia','bracbank','citybank','dutchbangl','ebl','islamibank','mtb','nbl','nccbank','primebank','sbacbank'}
def comparisons(db,slug):
    if slug not in {'primebank','dutchbangl','nccbank'}:return []
    metric='npl_ratio' if slug=='nccbank' else 'crar'
    facts=db.query(Fact).join(Institution).filter(Institution.slug.in_(BANKS),Fact.metric==metric).order_by(Fact.period_end.desc()).all();groups={}
    for row in facts:groups.setdefault(row.institution_id,[]).append(row)
    rows=[]
    for values in groups.values():
        current=values[0]
        if not current.source:continue
        previous=next((r for r in values if r.period_end.year==current.period_end.year-1),None)
        if metric=='npl_ratio' and (not previous or not previous.source):continue
        value=float(previous.value-current.value)*100 if metric=='npl_ratio' else float(current.value)*100
        rows.append(dict(bank_slug=current.institution.slug,name_bn=current.institution.name_bn,name_en=current.institution.name_en,value=round(value,6),source_url=current.source.url,previous_source_url=previous.source.url if metric=='npl_ratio' else None,as_of=current.period_end.isoformat(),previous_as_of=previous.period_end.isoformat() if metric=='npl_ratio' else None))
    rows.sort(key=lambda r:(-r['value'],r['bank_slug']))
    return [dict(metric=metric,title_bn='প্রকাশিত খেলাপি ঋণের বার্ষিক হ্রাস' if metric=='npl_ratio' else 'প্রকাশিত মূলধন অনুপাতের তুলনা',title_en='Published annual NPL decrease' if metric=='npl_ratio' else 'Published capital ratio comparison',rows=rows)] if rows else []
