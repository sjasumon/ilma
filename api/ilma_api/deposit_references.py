"""Source-linked context mentioned in fixed deposit recordings; no cross-audience ranking."""
def references(result,product,months,audience):
    out=[]
    for bank in result['catalog_banks']:
        for row in bank['rates']:
            p,a=row['product_type'],row['audience'];terms=row['tenor_list_months'];slug=bank['slug']
            selected=p==product and a==audience and (p=='savings' or months in terms)
            extra=False
            if product=='fdr' and audience=='all':
                extra=(months==1 and p=='fdr' and a=='all' and 3 in terms) or (months==6 and slug=='primebank' and p=='fdr' and a=='all' and 12 in terms) or (months==24 and slug=='nccbank' and p=='fdr' and a=='all' and 12 in terms) or (months==36 and slug=='bankasia' and p=='fdr' and a=='senior' and 36 in terms)
            elif product=='dps' and audience=='all':
                extra=(months==12 and slug=='bracbank' and p=='dps' and a=='all' and 120 in terms) or (months==36 and slug=='bankasia' and p=='dps' and a=='women' and 36 in terms)
            elif product=='savings' and audience=='all':
                extra=(slug=='nccbank' and a=='check' and p=='savings') or (slug in {'bankasia','primebank','bracbank','citybank','nccbank'} and p=='fdr' and a=='all' and 12 in terms and 'extra value' not in row['product'].lower())
            if audience in {'women','senior','student_child','nrb'}:
                extra=extra or p=='savings' and a==audience
                if audience=='senior':extra=extra or slug=='bankasia' and p=='fdr' and a=='all' and 36 in terms or slug=='bracbank' and p=='savings' and a=='all'
            if selected or extra:out.append(dict(bank_slug=slug,bank_name_bn=bank['name_bn'],bank_name_en=bank['name_en'],risk_code=bank['status']['code'],reference_only=True,offer=row))
    return out
