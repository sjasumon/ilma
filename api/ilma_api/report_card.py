from datetime import date
from decimal import Decimal
from typing import Any
import numpy as np

from sqlalchemy.orm import Session
from ilma_api.db import Institution, Fact, Rating, Rate, Event, InsuranceRule, SharePriceFlag, Source
from ilma_api.rules.status import evaluate, EvalResult, months_between
from ilma_api.rules.ratings import normalize_rating
from ilma_api.rules.reasons import format_percent, format_crore, to_bn_digits, format_date

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
                    "quote": f.quote
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
                "quote": r.quote
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
    median_fdr = float(np.median(all_fdr_rates)) if all_fdr_rates else 0.0825

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
        "text_en": ins_rule.text_en if ins_rule else ""
    }

    # 7 Health Checks (Core feature #2)
    crar_f = latest_facts.get("crar")
    npl_f = latest_facts.get("npl_ratio")
    profit_f = latest_facts.get("net_profit")
    rating_top = ratings_data[0] if ratings_data else None

    # Check 1: Capital Adequacy (CRAR)
    if crar_f:
        c_val = crar_f["value"]
        if c_val >= 0.125:
            c_status = "pass"
            c_desc_bn = "আইনি ন্যূনতম ১০.০০% ও বাফারের বেশি"
            c_desc_en = "Comfortably above 10% legal requirement"
        elif c_val >= 0.10:
            c_status = "watch"
            c_desc_bn = "আইনি সীমার কাছাকাছি (সতর্কতা)"
            c_desc_en = "Close to regulatory minimum"
        else:
            c_status = "fail"
            c_desc_bn = "আইনি ন্যূনতম সীমার নিচে"
            c_desc_en = "Below statutory minimum"
        c_val_text = f"{format_percent(c_val, bn=True)}%"
    else:
        c_status = "unknown"
        c_val_text = "তথ্য কম"
        c_desc_bn = "নিরীক্ষিত অনুপাত অপ্রাপ্য"
        c_desc_en = "Audited data not available"

    # Check 2: Bad Loans (NPL)
    if npl_f:
        n_val = npl_f["value"]
        if n_val < 0.10:
            n_status = "pass"
            n_desc_bn = "স্বাভাবিক ও সহনীয় সীমার মধ্যে"
            n_desc_en = "Within safe threshold"
        elif n_val < 0.25:
            n_status = "watch"
            n_desc_bn = "১০% থেকে ২৫% এর মধ্যে (উদ্বেগজনক)"
            n_desc_en = "Elevated between 10% and 25%"
        else:
            n_status = "fail"
            n_desc_bn = "২৫% বা তার বেশি (উচ্চ ঝুঁকি)"
            n_desc_en = "High risk >= 25%"
        n_val_text = f"{format_percent(n_val, bn=True)}%"
    else:
        n_status = "unknown"
        n_val_text = "তথ্য কম"
        n_desc_bn = "সর্বশেষ হিসাব অপ্রাপ্য"
        n_desc_en = "Latest figure not found"

    # Check 3: Net Profit
    if profit_f:
        p_val = profit_f["value"]
        if p_val > 0:
            p_status = "pass"
            p_val_text = f"{format_crore(p_val, bn=True)} কোটি টাকা"
            p_desc_bn = "মুনাফাজনক অবস্থানে রয়েছে"
            p_desc_en = "Profitable operation"
        else:
            p_status = "fail"
            p_val_text = f"লোকসান {format_crore(p_val, bn=True)} কোটি"
            p_desc_bn = "গত অর্থবছরে লোকসান হয়েছে"
            p_desc_en = "Net loss in recent period"
    else:
        p_status = "unknown"
        p_val_text = "তথ্য কম"
        p_desc_bn = "নিরীক্ষিত মুনাফা পাওয়া যায়নি"
        p_desc_en = "Profit data not available"

    # Check 4: Rating
    if rating_top:
        r_val_text = normalize_rating(rating_top["long_term"])
        r_agency = rating_top["agency"]
        r_out = rating_top["outlook"] or "stable"
        if r_val_text is None:
            r_status = "unknown"
            r_val_text = "—"
            r_desc_bn = "রেটিং বোঝা যায়নি"
            r_desc_en = "Unrecognized rating"
        elif r_val_text in ["AAA", "AA+", "AA", "AA-", "A+", "A", "A-"] and r_out in ["stable", "positive"]:
            r_status = "pass"
            r_desc_bn = f"{r_agency} রেটিং {r_val_text}, পূর্বাভাস স্থির"
            r_desc_en = f"{r_agency} rating {r_val_text}, stable"
        elif r_val_text in ["BBB+", "BBB", "BBB-"] or r_out == "negative":
            r_status = "watch"
            r_desc_bn = f"{r_agency} রেটিং {r_val_text} (সতর্কতামূলক)"
            r_desc_en = f"{r_agency} rating {r_val_text} (watch)"
        else:
            r_status = "fail"
            r_desc_bn = f"{r_agency} রেটিং {r_val_text} (ঝুঁকিপূর্ণ)"
            r_desc_en = f"{r_agency} rating {r_val_text} (high risk)"
    else:
        r_status = "unknown"
        r_val_text = "রেটিং নেই"
        r_desc_bn = "কোনো এজেন্সি রেটিং পাওয়া যায়নি"
        r_desc_en = "No rating found"

    # Check 5: Liquidity
    has_emergency_liq = any(ev["type"] == "emergency_liquidity" and ev["official"] and 0 <= months_between(ev["event_date"], as_of) <= 12 for ev in events_data)
    has_withdrawal_limit = any(ev["type"] == "withdrawal_limit" and ev["official"] and 0 <= months_between(ev["event_date"], as_of) <= 12 for ev in events_data)
    if has_withdrawal_limit:
        l_status = "fail"
        l_val_text = "উত্তোলন সীমা জারি"
        l_desc_bn = "টাকা তোলায় বিধিনিষেধ রয়েছে"
        l_desc_en = "Withdrawal limits imposed"
    elif has_emergency_liq:
        l_status = "watch"
        l_val_text = "জরুরি সহায়তা গৃহীত"
        l_desc_bn = "বাংলাদেশ ব্যাংকের জরুরি সহায়তা নিয়েছে"
        l_desc_en = "Received emergency liquidity"
    else:
        l_status = "pass"
        l_val_text = "স্বাভাবিক"
        l_desc_bn = "তারল্যে কোনো বিধিনিষেধ নেই"
        l_desc_en = "Normal liquidity operations"

    # Check 6: Regulator action
    h1_events = [ev for ev in events_data if ev["official"] and 0 <= months_between(ev["event_date"], as_of) <= 24 and ev["type"] in {"administrator", "board_dissolved", "forced_merger", "licence_cancelled", "liquidation"}]
    penalty_events = [ev for ev in events_data if ev["official"] and 0 <= months_between(ev["event_date"], as_of) <= 24 and ev["type"] == "penalty" and (ev["severity"] or 0) >= 3]
    if h1_events:
        reg_status = "fail"
        reg_val_text = "কঠোর পদক্ষেপ"
        reg_desc_bn = f"বাংলাদেশ ব্যাংক {h1_events[0]['title_bn']}"
        reg_desc_en = f"Bangladesh Bank {h1_events[0]['title_en']}"
    elif penalty_events:
        reg_status = "watch"
        reg_val_text = "নিয়ন্ত্রক জরিমানা"
        reg_desc_bn = f"গুরুতর অনিয়মে জরিমানা করা হয়েছে"
        reg_desc_en = "Regulatory penalty recorded"
    else:
        reg_status = "pass"
        reg_val_text = "কোনো বিধিনিষেধ নেই"
        reg_desc_bn = "পরিচালনা পর্ষদ ও কার্যক্রম স্বাভাবিক"
        reg_desc_en = "No punitive regulatory actions"

    # Check 7: Deposit Insurance
    if inst.type == "bank":
        ins_status = "pass"
        ins_val_text = "২ লাখ টাকা পর্যন্ত"
        ins_desc_bn = "আইন ২০২৬ অনুযায়ী শতভাগ আমানত বীমাযুক্ত"
        ins_desc_en = "100% insured up to Tk 2 Lakh"
    else:
        ins_status = "watch"
        ins_val_text = "বীমা প্রযোজ্য নয়"
        ins_desc_bn = "আর্থিক প্রতিষ্ঠানে বীমা সুরক্ষা ২০২৮ থেকে কার্যকর হবে"
        ins_desc_en = "NBFI coverage starts July 2028"

    checks_list = [
        {"id": "capital", "name_bn": "মূলধন পর্যাপ্ততা (CRAR)", "name_en": "Capital Adequacy (CRAR)", "status": c_status, "value_text": c_val_text, "desc_bn": c_desc_bn, "desc_en": c_desc_en},
        {"id": "npl", "name_bn": "খেলাপি ঋণ (NPL)", "name_en": "Bad Loans (NPL Ratio)", "status": n_status, "value_text": n_val_text, "desc_bn": n_desc_bn, "desc_en": n_desc_en},
        {"id": "profit", "name_bn": "নিট মুনাফা", "name_en": "Net Profit", "status": p_status, "value_text": p_val_text, "desc_bn": p_desc_bn, "desc_en": p_desc_en},
        {"id": "rating", "name_bn": "ক্রেডিট রেটিং", "name_en": "Credit Rating", "status": r_status, "value_text": r_val_text, "desc_bn": r_desc_bn, "desc_en": r_desc_en},
        {"id": "liquidity", "name_bn": "তারল্য অবস্থা", "name_en": "Liquidity", "status": l_status, "value_text": l_val_text, "desc_bn": l_desc_bn, "desc_en": l_desc_en},
        {"id": "regulator", "name_bn": "নিয়ন্ত্রক পদক্ষেপ", "name_en": "Regulatory Cleanliness", "status": reg_status, "value_text": reg_val_text, "desc_bn": reg_desc_bn, "desc_en": reg_desc_en},
        {"id": "insurance", "name_bn": "আমানত বীমা সুরক্ষা", "name_en": "Deposit Insurance Coverage", "status": ins_status, "value_text": ins_val_text, "desc_bn": ins_desc_bn, "desc_en": ins_desc_en}
    ]

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
        "rates": {
            "as_of": str(rates_dict["fdr_12m"]["as_of"]) if "fdr_12m" in rates_dict else None,
            "fdr_12m": rates_dict["fdr_12m"]["rate"] if "fdr_12m" in rates_dict else None,
            "sector_median_fdr_12m": median_fdr,
            "source_url": rates_dict["fdr_12m"]["source_info"]["url"] if "fdr_12m" in rates_dict else None
        },
        "checks": checks_list,
        "data_date": str(newest_checked_on),
        "release_id": "seed-2026-10-27-01",
        "disclaimer_key": "VS-08"
    }
