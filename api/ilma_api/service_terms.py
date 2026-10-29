"""Published deposit terms: ranges stay ranges; discrete options stay discrete."""
import re

_EXPRESSION=re.compile(r'(?<![\w.])((?:\d+\s*(?:[my]\b)?\s*(?:to|or|and|,|&|[-–])\s*)*\d+)\s*(months?|years?|[my])\b',re.I)


def parse_terms(product='',condition='',exact=None):
    text=(condition+' '+product).translate(str.maketrans('০১২৩৪৫৬৭৮৯','0123456789'))
    matches=list(_EXPRESSION.finditer(text));ranges=[];options=set()
    for match in matches:
        numbers=[int(n) for n in re.findall(r'\d+',match[1])]
        multiplier=12 if match[2].lower().startswith('y') else 1
        values=[n*multiplier for n in numbers if 0<n*multiplier<=600]
        if not values:continue
        if len(values)==2 and re.search(r'\bto\b|[-–]',match[1],re.I):ranges.append((min(values),max(values)))
        else:options.update(values)
    if ranges:
        low,high=max(ranges,key=lambda pair:pair[1]-pair[0])
        return {'tenor_min_months':low,'tenor_max_months':high,'tenor_options':None}
    if len(options)>1:return {'tenor_min_months':min(options),'tenor_max_months':max(options),'tenor_options':sorted(options)}
    if exact is not None:options={exact}
    if options:
        value=next(iter(options));return {'tenor_min_months':value,'tenor_max_months':value,'tenor_options':[value]}
    return {'tenor_min_months':None,'tenor_max_months':None,'tenor_options':None}


def terms(row):
    values={key:getattr(row,key,None) for key in ('tenor_min_months','tenor_max_months','tenor_options')}
    if values['tenor_min_months'] is None:return parse_terms(row.product,row.condition,row.tenor_months)
    return values


def matches_term(row,months):
    if months is None:return True
    info=terms(row)
    if info['tenor_options']:return months in info['tenor_options']
    return info['tenor_min_months'] is not None and info['tenor_min_months']<=months<=info['tenor_max_months']


def nearest_term(row,months):
    info=terms(row)
    if months is None:return info['tenor_min_months'] or row.tenor_months
    if matches_term(row,months):return months
    if info['tenor_options']:return min(info['tenor_options'],key=lambda n:(abs(n-months),n))
    if info['tenor_min_months'] is not None:return max(info['tenor_min_months'],min(months,info['tenor_max_months']))
    return None
