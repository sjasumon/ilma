from datetime import date
from typing import Any
import numpy as np

from sqlalchemy.orm import Session
from ilma_api.db import Institution, Fact, Rating, Rate, Event, InsuranceRule, SharePriceFlag, Source, Release, ServiceOffer
from ilma_api.rules.status import evaluate, EvalResult

def get_institution_report_card(db: Session, institution_id_or_slug: int | str, as_of: date | None = None) -> dict[str, Any] | None:
    if as_of is None:
        as_of = date.today()

    if isinstance(institution_id_or_slug, int) or (isinstance(institution_id_or_slug, str) and institution_id_or_slug.isdigit()):
        inst = db.query(Institution).filter_by(id=int(institution_id_or_slug)).first()
    else:
        inst = db.query(Institution).filter_by(slug=institution_id_or_slug).first()

    if not inst:
        return None

    # Handle licence_only coverage
    if inst.coverage == "licence_only":
        return {
            "institution": {
                "id": inst.id,
                "slug": inst.slug,
                "name_bn": inst.name_bn,
                "name_en": inst.name_en,
                "type": inst.type,
                "islamic": inst.islamic,
                "licensed": inst.licensed,
                "listed": inst.listed,
                "coverage": inst.coverage
            },
            "status": None,
            "message_bn": "প্রতিষ্ঠানটি শুধুমাত্র লাইসেন্সপ্রাপ্ত হিসেবে অন্তর্ভুক্ত। আর্থিক তথ্য এখনও সংগৃহীত হয়নি।",
            "message_en": "This institution is listed as licensed only. Financial data is not yet available."
        }

    # Gather facts
    facts_rows = db.query(Fact).filter_by(institution_id=inst.id).order_by(Fact.period_end.desc()).all()
    latest_facts: dict[str, dict[str, Any]] = {}
    newest_checked_on = date(2026, 1, 1)

    for f in facts_rows:
        if f.checked_on and f.checked_on > newest_checked_on:
            newest_checked_on = f.checked_on
        if f.metric not in latest_facts:
            src = db.query(Source).filter_by(source_id=f.source_id).first()
            latest_facts[f.metric] = {
                "fact_id": f.fact_id,
                "metric": f.metric,
                "value": float(f.value),
                "unit": f.unit,
                "period": f.period,
                "period_end": f.period_end,
                "quote": f.quote,
                "source_info": {
                    "source_id": src.source_id if src else None,
                    "url": src.url if src else None,
                    "title": src.title if src else None,
                    "publisher": src.publisher if src else None,
                    "published_at": src.published_at if src else None,
                    "page": src.page if src else None,
                    "quote": f.quote,
                    "checked": f.checked_by.casefold() == 'sumon'
                } if src else {}
            }

    # Gather ratings
    ratings_rows = db.query(Rating).filter_by(institution_id=inst.id).order_by(Rating.rated_on.desc()).all()
    ratings_data: list[dict[str, Any]] = []
    for r in ratings_rows:
        if r.checked_on and r.checked_on > newest_checked_on:
            newest_checked_on = r.checked_on
        src = db.query(Source).filter_by(source_id=r.source_id).first()
        ratings_data.append({
            "fact_id": r.fact_id,
            "agency": r.agency,
            "long_term": r.long_term,
            "short_term": r.short_term,
            "outlook": r.outlook,
            "rated_on": r.rated_on,
            "valid_to": r.valid_to,
            "quote": r.quote,
            "source_info": {
                "source_id": src.source_id if src else None,
                "url": src.url if src else None,
                "title": src.title if src else None,
                "publisher": src.publisher if src else None,
                "published_at": src.published_at if src else None,
                "page": src.page if src else None,
                "quote": r.quote,
                "checked": r.checked_by.casefold() == 'sumon'
            } if src else {}
        })

    # Gather events
    events_rows = db.query(Event).filter_by(institution_id=inst.id).order_by(Event.event_date.desc()).all()
    events_data: list[dict[str, Any]] = []
    for ev in events_rows:
        if ev.checked_on and ev.checked_on > newest_checked_on:
            newest_checked_on = ev.checked_on
        src = ev.sources[0] if ev.sources else None
        events_data.append({
            "event_id": ev.event_id,
            "type": ev.type,
            "title_bn": ev.title_bn,
            "title_en": ev.title_en,
            "status": ev.status,
            "official": ev.official,
            "severity": ev.severity,
            "event_date": ev.event_date,
            "last_update": ev.last_update,
            "source_info": {
                "source_id": src.source_id if src else None,
                "url": src.url if src else None,
                "title": src.title if src else None,
                "publisher": src.publisher if src else None,
                "published_at": src.published_at if src else None,
                "page": src.page if src else None,
                "quote": ""
            } if src else {}
        })

    # Gather rates & median
    latest_rates = {}
    for rate_row in db.query(Rate).filter_by(product="fdr", tenor_months=12).order_by(Rate.as_of.desc()).all():
        latest_rates.setdefault(rate_row.institution_id, float(rate_row.rate))
    all_fdr_rates = list(latest_rates.values())
    median_fdr = float(np.median(all_fdr_rates)) if all_fdr_rates else None

    inst_rate_row = db.query(Rate).filter_by(institution_id=inst.id, product="fdr", tenor_months=12).order_by(Rate.as_of.desc()).first()
    rates_dict = {}
    if inst_rate_row:
        src = db.query(Source).filter_by(source_id=inst_rate_row.source_id).first()
        rates_dict["fdr_12m"] = {
            "fact_id": inst_rate_row.fact_id,
            "rate": float(inst_rate_row.rate),
            "as_of": inst_rate_row.as_of,
            "source_info": {
                "url": src.url if src else None,
                "title": src.title if src else None,
                "quote": inst_rate_row.quote
            }
        }

    # The current service export supersedes legacy deposit-rate fixtures.
    service_rates = db.query(ServiceOffer).filter_by(product_type='fdr', tenor_months=12,
        attribute='rate', basis='conventional', hidden=False).all()
    if service_rates:
        chosen = {}
        eligible = [row for row in service_rates if row.value_num is not None and not row.stale and (as_of-row.doc_date).days<=365]
        eligible.sort(key=lambda row:(any(word in row.product.lower() for word in ('extra','plus','senior','women','million','kotipoti')),-row.doc_date.toordinal(),row.product,row.value_num,row.condition,row.offer_id))
        for row in eligible:chosen.setdefault(row.institution_id,row)
        median_fdr=float(np.median([float(row.value_num)/100 for row in chosen.values()])) if chosen else None
        rates_dict={}
        current=chosen.get(inst.id)
        if current:
            rates_dict['fdr_12m']=dict(fact_id=current.offer_id,rate=float(current.value_num)/100,as_of=current.doc_date,
                source_info=dict(url=current.source_url,title=current.product,quote=current.quote,
                    page=current.page,published_at=current.doc_date))

    # Share price flag
    spf = db.query(SharePriceFlag).filter_by(institution_id=inst.id).first()
    spf_dict = None
    if spf:
        src = db.query(Source).filter_by(source_id=spf.source_id).first()
        spf_dict = {
            "days_below_face": spf.days_below_face,
            "window_end": spf.window_end,
            "source_info": {"url": src.url if src else None, "title": src.title if src else None}
        }

    # Evaluate rules
    inst_dict = {
        "id": inst.id, "slug": inst.slug, "name_bn": inst.name_bn, "name_en": inst.name_en,
        "type": inst.type, "islamic": inst.islamic, "licensed": inst.licensed,
        "listed": inst.listed, "coverage": inst.coverage
    }
    data_dict = {
        "facts": latest_facts,
        "ratings": ratings_data,
        "events": events_data,
        "rates": rates_dict,
        "median_12m_fdr": median_fdr,
        "share_price_flag": spf_dict
    }

    eval_res: EvalResult = evaluate(inst_dict, data_dict, as_of=as_of)

    # Insurance rule
    ins_rule = db.query(InsuranceRule).filter_by(inst_type=inst.type).first()
    insurance_data = {
        "covered": ins_rule.covered if ins_rule else False,
        "limit_bdt": ins_rule.limit_bdt if ins_rule else None,
        "payout_working_days": ins_rule.payout_working_days if ins_rule else None,
        "text_bn": ins_rule.text_bn if ins_rule else "",
        "text_en": ins_rule.text_en if ins_rule else "",
        "source_url": ins_rule.source.url if ins_rule and ins_rule.source else None,
        "source_title": ins_rule.source.title if ins_rule and ins_rule.source else None
    }

    release = db.query(Release).order_by(Release.loaded_at.desc()).first()
    from ilma_api.incidents import records
    incident_count=len(records(db,inst.id))
    return {
        "institution": inst_dict,
        "status": {
            "code": eval_res.code,
            "label_bn": eval_res.label_bn,
            "label_en": eval_res.label_en,
            "rules_version": eval_res.rules_version
        },
        "reasons": eval_res.reasons,
        "insurance": insurance_data,
        "ratings": ratings_data,
        "figures": list(latest_facts.values()),
        "events": events_data[:5],
        "incident_count": incident_count,
        "rates": {
            "as_of": str(rates_dict["fdr_12m"]["as_of"]) if "fdr_12m" in rates_dict else None,
            "fdr_12m": rates_dict["fdr_12m"]["rate"] if "fdr_12m" in rates_dict else None,
            "sector_median_fdr_12m": median_fdr,
            "source_url": rates_dict["fdr_12m"]["source_info"]["url"] if "fdr_12m" in rates_dict else None
        },
        "data_date": str(max((f.period_end for f in facts_rows), default=as_of)) if facts_rows else None,
        "updated_at": str(newest_checked_on) if facts_rows or ratings_rows or events_rows else None,
        "not_checked_bn": "বাংলাদেশ ব্যাংকের ব্যবস্থা ও জরিমানা এই ডেমোতে যাচাই করা হয়নি।",
        "not_checked_en": "Bangladesh Bank actions and penalties were not checked in this demo.",
        "release_id": release.release_id if release else None,
        "disclaimer_key": "VS-08"
    }
