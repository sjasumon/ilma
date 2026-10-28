from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any
import json
from pathlib import Path

from ilma_api.rules.ratings import is_at_or_below, is_at_or_above, normalize_rating, SCALE_INDEX
from ilma_api.rules.reasons import (
    format_percent, format_crore, format_date, to_bn_digits, check_forbidden_words
)

@dataclass
class Trigger:
    rule_id: str
    fact_or_event_id: str | None
    source_info: dict[str, Any]
    text_bn: str
    text_en: str

@dataclass
class EvalResult:
    code: str
    label_bn: str
    label_en: str
    triggers: list[Trigger]
    reasons: list[dict[str, Any]]
    rules_version: str

STATUS_LABELS = {
    "strong": ("ভালো অবস্থা", "Strong"),
    "watch": ("সতর্ক থাকুন", "Watch"),
    "high": ("ঝুঁকি বেশি", "High risk"),
    "no_data": ("তথ্য কম", "Not enough data")
}

def months_between(d1: date, d2: date) -> int:
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)

def evaluate(inst: dict, data: dict, as_of: date, cfg: dict | None = None) -> EvalResult:
    if cfg is None:
        cfg_path = Path(__file__).parent / "thresholds.json"
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            
    # rules_version has no default: serving statuses stamped with a version
    # that never shipped would mislabel every report card.
    rules_version = cfg["rules_version"]
    crar_min = cfg.get("crar_min", 0.10)
    crar_buffer = cfg.get("crar_buffer", 0.025)
    npl_high = cfg.get("npl_high", 0.25)
    npl_watch = cfg.get("npl_watch", 0.10)
    rating_high_at_or_below = cfg.get("rating_high_at_or_below", "BB+")
    fdr_premium_pp = cfg.get("fdr_premium_pp", 0.02)
    share_below_face_days = cfg.get("share_below_face_days", 60)
    figures_max_age_months = cfg.get("figures_max_age_months", 18)
    penalty_min_severity = cfg.get("penalty_min_severity", 3)
    windows = cfg.get("windows_months", {})

    facts = data.get("facts", {}) # metric -> row
    ratings = data.get("ratings", []) # sorted desc by rated_on
    # Defence in depth for B1: the loaders reject future-dated events, but a
    # future row must never flip a status window even if one slips through.
    events = [ev for ev in data.get("events", []) # sorted desc by event_date
              if not ev.get("event_date") or ev.get("event_date") <= as_of]
    rates = data.get("rates", {})
    share_price_flag = data.get("share_price_flag")
    median_fdr = data.get("median_12m_fdr", 0.0)

    high_triggers: list[Trigger] = []
    watch_triggers: list[Trigger] = []
    positive_facts: list[Trigger] = []

    # High triggers
    # H1: administrator, board_dissolved, forced_merger, licence_cancelled, liquidation
    h1_types = {"administrator", "board_dissolved", "forced_merger", "licence_cancelled", "liquidation"}
    action_map_bn = {
        "administrator": "প্রশাসক নিয়োগ",
        "board_dissolved": "পরিচালনা পর্ষদ ভেঙে",
        "forced_merger": "একীভূত করার আদেশ",
        "licence_cancelled": "লাইসেন্স বাতিল",
        "liquidation": "অবসায়নের উদ্যোগ"
    }
    action_map_en = {
        "administrator": "appointed an administrator",
        "board_dissolved": "dissolved the board",
        "forced_merger": "ordered a merger",
        "licence_cancelled": "cancelled the licence",
        "liquidation": "initiated liquidation"
    }
    for ev in events:
        if ev.get("official") and ev.get("type") in h1_types:
            ed = ev.get("event_date")
            if ed and months_between(ed, as_of) <= windows.get("H1", 24):
                act_bn = action_map_bn.get(ev.get("type"), ev.get("title_bn", ""))
                act_en = action_map_en.get(ev.get("type"), ev.get("title_en", ""))
                d_bn = format_date(ed, bn=True)
                d_en = format_date(ed, bn=False)
                high_triggers.append(Trigger(
                    rule_id="H1",
                    fact_or_event_id=ev.get("event_id"),
                    source_info=ev.get("source_info", {}),
                    text_bn=f"বাংলাদেশ ব্যাংক {act_bn} করেছে ({d_bn})।",
                    text_en=f"Bangladesh Bank {act_en} ({d_en})."
                ))
                break

    # H2: withdrawal_limit
    for ev in events:
        if ev.get("official") and ev.get("type") == "withdrawal_limit":
            ed = ev.get("event_date")
            if ed and months_between(ed, as_of) <= windows.get("H2", 12):
                src_title = ev.get("source_info", {}).get("title", "বাংলাদেশ ব্যাংক")
                high_triggers.append(Trigger(
                    rule_id="H2",
                    fact_or_event_id=ev.get("event_id"),
                    source_info=ev.get("source_info", {}),
                    text_bn=f"টাকা তোলায় সীমা দেওয়া হয়েছে ({format_date(ed, bn=True)}, {src_title})।",
                    text_en=f"Limits on withdrawals were imposed ({format_date(ed, bn=False)}, {src_title})."
                ))
                break

    # H3: latest crar < crar_min
    crar_row = facts.get("crar")
    if crar_row and crar_row.get("value") is not None:
        crar_val = float(crar_row["value"])
        if crar_val < crar_min:
            period = crar_row.get("period", "")
            period_bn = to_bn_digits(period)
            high_triggers.append(Trigger(
                rule_id="H3",
                fact_or_event_id=crar_row.get("fact_id"),
                source_info=crar_row.get("source_info", {}),
                text_bn=f"মূলধন অনুপাত {format_percent(crar_val, bn=True)}%, যা ন্যূনতম সীমার ({format_percent(crar_min, bn=True)}%) চেয়ে কম ({period_bn})।",
                text_en=f"Capital ratio {format_percent(crar_val)}%, below the minimum ({format_percent(crar_min)}%) ({period})."
            ))

    # H4: latest npl_ratio >= 0.25
    npl_row = facts.get("npl_ratio")
    # Ratios derived from quoted amounts are labelled, never shown as reported.
    calculated = bool(npl_row and str(npl_row.get("basis") or "").endswith("_calculated"))
    calc_bn = ", নিরীক্ষকের প্রতিবেদন থেকে হিসাব করা" if calculated else ""
    calc_en = ", calculated from the auditor's report" if calculated else ""
    if npl_row and npl_row.get("value") is not None:
        npl_val = float(npl_row["value"])
        if npl_val >= npl_high:
            period = npl_row.get("period", "")
            period_bn = to_bn_digits(period)
            pct_bn = format_percent(npl_val, bn=True)
            pct_en = format_percent(npl_val, bn=False)
            high_triggers.append(Trigger(
                rule_id="H4",
                fact_or_event_id=npl_row.get("fact_id"),
                source_info=npl_row.get("source_info", {}),
                text_bn=f"খেলাপি ঋণ {pct_bn}% — প্রতি ১০০ টাকার ঋণে {pct_bn} টাকা ফেরত আসছে না ({period_bn}{calc_bn})।",
                text_en=f"Bad loans {pct_en}% — of every Tk 100 lent, Tk {pct_en} is not being repaid ({period}{calc_en})."
            ))

    # H5: latest long-term rating BB+ or lower
    latest_rating = ratings[0] if ratings else None
    if latest_rating and latest_rating.get("long_term"):
        lt = latest_rating["long_term"]
        if is_at_or_below(lt, rating_high_at_or_below):
            agency = latest_rating.get("agency", "")
            rd = latest_rating.get("rated_on")
            high_triggers.append(Trigger(
                rule_id="H5",
                fact_or_event_id=latest_rating.get("fact_id"),
                source_info=latest_rating.get("source_info", {}),
                text_bn=f"দীর্ঘমেয়াদি রেটিং {lt} ({agency}, {format_date(rd, bn=True) if rd else ''})।",
                text_en=f"Long-term rating {lt} ({agency}, {format_date(rd, bn=False) if rd else ''})."
            ))

    # Watch triggers
    # W1: 0.10 <= npl < 0.25
    if npl_row and npl_row.get("value") is not None:
        npl_val = float(npl_row["value"])
        if npl_watch <= npl_val < npl_high:
            period = npl_row.get("period", "")
            period_bn = to_bn_digits(period)
            watch_triggers.append(Trigger(
                rule_id="W1",
                fact_or_event_id=npl_row.get("fact_id"),
                source_info=npl_row.get("source_info", {}),
                text_bn=f"খেলাপি ঋণ {format_percent(npl_val, bn=True)}% ({period_bn}{calc_bn})।",
                text_en=f"Bad loans {format_percent(npl_val)}% ({period}{calc_en})."
            ))

    # W2: crar_min <= crar < crar_min + crar_buffer
    if crar_row and crar_row.get("value") is not None:
        crar_val = float(crar_row["value"])
        if crar_min <= crar_val < (crar_min + crar_buffer):
            period = crar_row.get("period", "")
            period_bn = to_bn_digits(period)
            watch_triggers.append(Trigger(
                rule_id="W2",
                fact_or_event_id=crar_row.get("fact_id"),
                source_info=crar_row.get("source_info", {}),
                text_bn=f"মূলধন অনুপাত {format_percent(crar_val, bn=True)}%, ন্যূনতম সীমার কাছাকাছি ({period_bn})।",
                text_en=f"Capital ratio {format_percent(crar_val)}%, close to the minimum ({period})."
            ))

    # W3: rating downgrade within 12m, outlook negative/developing, or latest rating BBB+, BBB, BBB-
    if latest_rating:
        lt = latest_rating.get("long_term", "")
        agency = latest_rating.get("agency", "")
        rd = latest_rating.get("rated_on")
        outlook = latest_rating.get("outlook", "")
        is_w3 = False
        ot_bn, ot_en = "", ""
        if outlook == "negative":
            is_w3 = True
            ot_bn = ", পূর্বাভাস নেতিবাচক"
            ot_en = ", outlook negative"
        elif outlook == "developing":
            # Developing means the agency sees the direction as uncertain.
            is_w3 = True
            ot_bn = ", পূর্বাভাস অনিশ্চিত"
            ot_en = ", outlook developing (uncertain)"
        elif lt in {"BBB+", "BBB", "BBB-"}:
            is_w3 = True
        
        # Check downgrade within 12 months for same agency
        if not is_w3 and len(ratings) > 1 and rd and months_between(rd, as_of) <= windows.get("W3", 12):
            prev = next((r for r in ratings[1:] if r.get("agency") == agency), None)
            if prev and prev.get("long_term"):
                curr_idx = SCALE_INDEX.get(normalize_rating(lt) or "", 999)
                prev_idx = SCALE_INDEX.get(normalize_rating(prev["long_term"]) or "", 999)
                if curr_idx > prev_idx:
                    is_w3 = True
                    ot_bn = ", রেটিং অবনমন"
                    ot_en = ", lowered"

        if is_w3:
            watch_triggers.append(Trigger(
                rule_id="W3",
                fact_or_event_id=latest_rating.get("fact_id"),
                source_info=latest_rating.get("source_info", {}),
                text_bn=f"রেটিং {lt}{ot_bn} ({agency}, {format_date(rd, bn=True) if rd else ''})।",
                text_en=f"Rating {lt}{ot_en} ({agency}, {format_date(rd, bn=False) if rd else ''})."
            ))

    # W4: penalty severity >= 3 within 24m or fraud_case case_filed+
    for ev in events:
        ed = ev.get("event_date")
        if not ed or months_between(ed, as_of) > windows.get("W4", 24):
            continue
        ev_type = ev.get("type")
        status = ev.get("status")
        is_penalty = (ev_type == "penalty" and ev.get("official") and (ev.get("severity", 0) or 0) >= penalty_min_severity)
        is_fraud = (ev_type == "fraud_case" and status in {"case_filed", "charged", "convicted"})
        if is_penalty or is_fraud:
            t_bn = ev.get("title_bn", "")
            t_en = ev.get("title_en", "")
            status_labels_bn = {"case_filed": "মামলা দায়ের", "charged": "চার্জশিটভুক্ত", "convicted": "দণ্ডপ্রাপ্ত", "official": "নিয়ন্ত্রক জরিমানা"}
            status_labels_en = {"case_filed": "case filed", "charged": "charged", "convicted": "convicted", "official": "penalty imposed"}
            sl_bn = status_labels_bn.get(status, "অফিসিয়াল তথ্য")
            sl_en = status_labels_en.get(status, "official")
            watch_triggers.append(Trigger(
                rule_id="W4",
                fact_or_event_id=ev.get("event_id"),
                source_info=ev.get("source_info", {}),
                text_bn=f"{t_bn} — {sl_bn} ({format_date(ed, bn=True)})।",
                text_en=f"{t_en} — {sl_en} ({format_date(ed, bn=False)})."
            ))
            break

    # W5: latest provision_shortfall > 0 or provision_deferral official within latest report year
    prov_row = facts.get("provision_shortfall")
    if prov_row and prov_row.get("value") is not None and float(prov_row["value"]) > 0:
        amt = float(prov_row["value"])
        p = prov_row.get("period", "")
        watch_triggers.append(Trigger(
            rule_id="W5",
            fact_or_event_id=prov_row.get("fact_id"),
            source_info=prov_row.get("source_info", {}),
            text_bn=f"প্রভিশন ঘাটতি {format_crore(amt, bn=True)} কোটি টাকা ({to_bn_digits(p)})।",
            text_en=f"Provision shortfall Tk {format_crore(amt)} crore ({p})."
        ))
    else:
        for ev in events:
            if ev.get("type") == "provision_deferral" and ev.get("official"):
                ed = ev.get("event_date")
                if ed and months_between(ed, as_of) <= 12:
                    watch_triggers.append(Trigger(
                        rule_id="W5",
                        fact_or_event_id=ev.get("event_id"),
                        source_info=ev.get("source_info", {}),
                        text_bn=f"প্রভিশন সংরক্ষণে স্থগিতাদেশ দেওয়া হয়েছে ({format_date(ed, bn=True)})।",
                        text_en=f"Provision deferral granted ({format_date(ed, bn=False)})."
                    ))
                    break

    # W6: latest net_profit < 0
    profit_row = facts.get("net_profit")
    if profit_row and profit_row.get("value") is not None and float(profit_row["value"]) < 0:
        loss = abs(float(profit_row["value"]))
        p = profit_row.get("period", "")
        watch_triggers.append(Trigger(
            rule_id="W6",
            fact_or_event_id=profit_row.get("fact_id"),
            source_info=profit_row.get("source_info", {}),
            text_bn=f"গত বছর লোকসান {format_crore(loss, bn=True)} কোটি টাকা ({to_bn_digits(p)})।",
            text_en=f"Loss of Tk {format_crore(loss)} crore last year ({p})."
        ))

    # W7: 12-month FDR rate - median >= 0.02
    fdr_row = rates.get("fdr_12m")
    if fdr_row and fdr_row.get("rate") is not None and median_fdr > 0:
        fdr_val = float(fdr_row["rate"])
        diff = fdr_val - median_fdr
        if diff >= fdr_premium_pp:
            gap_pp = diff * 100
            watch_triggers.append(Trigger(
                rule_id="W7",
                fact_or_event_id=fdr_row.get("fact_id"),
                source_info=fdr_row.get("source_info", {}),
                text_bn=f"১ বছরের এফডিআর হার {format_percent(fdr_val, bn=True)}%, বেশিরভাগ ব্যাংকের চেয়ে {format_percent(diff, bn=True)} পয়েন্ট বেশি। অনেক সময় টাকার টানাটানিতে বেশি হার দেওয়া হয়।",
                text_en=f"1-year FDR rate {format_percent(fdr_val)}%, {format_percent(diff)} points above most banks. High rates are often offered when money is short."
            ))

    # W8: emergency_liquidity official within 12m
    for ev in events:
        if ev.get("type") == "emergency_liquidity" and ev.get("official"):
            ed = ev.get("event_date")
            if ed and months_between(ed, as_of) <= windows.get("W8", 12):
                watch_triggers.append(Trigger(
                    rule_id="W8",
                    fact_or_event_id=ev.get("event_id"),
                    source_info=ev.get("source_info", {}),
                    text_bn=f"বাংলাদেশ ব্যাংক জরুরি তারল্য সহায়তা দিয়েছে ({format_date(ed, bn=True)})।",
                    text_en=f"Bangladesh Bank gave emergency liquidity support ({format_date(ed, bn=False)})."
                ))
                break

    # W9: days_below_face >= 60 and window_end within 6m
    if share_price_flag:
        dbf = share_price_flag.get("days_below_face", 0)
        we = share_price_flag.get("window_end")
        if dbf >= share_below_face_days and we and months_between(we, as_of) <= windows.get("W9", 6):
            watch_triggers.append(Trigger(
                rule_id="W9",
                fact_or_event_id=None,
                source_info=share_price_flag.get("source_info", {}),
                text_bn=f"শেয়ারের দাম {to_bn_digits(dbf)} দিন ধরে অভিহিত মূল্যের নিচে।",
                text_en=f"Share price below face value for {dbf} days."
            ))

    # Positive facts (P1-P4)
    # P1: crar >= crar_min + buffer
    if crar_row and crar_row.get("value") is not None:
        crar_val = float(crar_row["value"])
        if crar_val >= (crar_min + crar_buffer):
            p = crar_row.get("period", "")
            positive_facts.append(Trigger(
                rule_id="P1",
                fact_or_event_id=crar_row.get("fact_id"),
                source_info=crar_row.get("source_info", {}),
                text_bn=f"মূলধন অনুপাত {format_percent(crar_val, bn=True)}%, আইনি ন্যূনতমের ({format_percent(crar_min, bn=True)}%) চেয়ে বেশি ({to_bn_digits(p)})।",
                text_en=f"Capital ratio {format_percent(crar_val)}%, above the legal minimum ({format_percent(crar_min)}%) ({p})."
            ))

    # P2: npl_ratio < npl_watch
    if npl_row and npl_row.get("value") is not None:
        npl_val = float(npl_row["value"])
        if npl_val < npl_watch:
            p = npl_row.get("period", "")
            positive_facts.append(Trigger(
                rule_id="P2",
                fact_or_event_id=npl_row.get("fact_id"),
                source_info=npl_row.get("source_info", {}),
                text_bn=f"খেলাপি ঋণ {format_percent(npl_val, bn=True)}%, যা কম ({to_bn_digits(p)})।",
                text_en=f"Bad loans {format_percent(npl_val)}%, which is low ({p})."
            ))

    # P3: latest rating is A- or better with no downgrade or negative outlook
    if latest_rating:
        lt = latest_rating.get("long_term", "")
        agency = latest_rating.get("agency", "")
        rd = latest_rating.get("rated_on")
        outlook = latest_rating.get("outlook", "stable")
        if is_at_or_above(lt, "A-") and outlook in {"stable", "positive"}:
            positive_facts.append(Trigger(
                rule_id="P3",
                fact_or_event_id=latest_rating.get("fact_id"),
                source_info=latest_rating.get("source_info", {}),
                text_bn=f"দীর্ঘমেয়াদি রেটিং {lt}, স্থির ({agency}, {format_date(rd, bn=True) if rd else ''})।",
                text_en=f"Long-term rating {lt}, stable ({agency}, {format_date(rd, bn=False) if rd else ''})."
            ))

    # P4: net_profit > 0
    if profit_row and profit_row.get("value") is not None and float(profit_row["value"]) > 0:
        prof = float(profit_row["value"])
        p = profit_row.get("period", "")
        positive_facts.append(Trigger(
            rule_id="P4",
            fact_or_event_id=profit_row.get("fact_id"),
            source_info=profit_row.get("source_info", {}),
            text_bn=f"গত বছর মুনাফা {format_crore(prof, bn=True)} কোটি টাকা ({to_bn_digits(p)})।",
            text_en=f"Profit of Tk {format_crore(prof)} crore last year ({p})."
        ))

    # Determine status code
    # Check no_data condition:
    # latest npl_ratio or latest crar is missing or period_end > 18 months before as_of, AND no High trigger applies
    is_missing_npl = (npl_row is None or npl_row.get("period_end") is None or months_between(npl_row["period_end"], as_of) > figures_max_age_months)
    is_missing_crar = (crar_row is None or crar_row.get("period_end") is None or months_between(crar_row["period_end"], as_of) > figures_max_age_months)
    
    status_code: str
    reasons_list: list[Trigger] = []

    if (is_missing_npl or is_missing_crar) and not high_triggers:
        status_code = "no_data"
        missing_item_bn = "বার্ষিক প্রতিবেদন ও নিরীক্ষিত তথ্য"
        missing_item_en = "annual report and audited figures"
        reasons_list.append(Trigger(
            rule_id="No data",
            fact_or_event_id=None,
            source_info={},
            text_bn=f"সর্বশেষ {missing_item_bn} পাওয়া যায়নি।",
            text_en=f"The latest {missing_item_en} was not found."
        ))
    elif high_triggers:
        status_code = "high"
    elif watch_triggers:
        status_code = "watch"
    else:
        status_code = "strong"

    # Assemble reasons (picking exactly 3)
    # 1. High triggers (order H1..H5)
    for t in high_triggers:
        if len(reasons_list) < 3 and t not in reasons_list:
            reasons_list.append(t)
    # 2. Watch triggers (order W1..W9)
    for t in watch_triggers:
        if len(reasons_list) < 3 and t not in reasons_list:
            reasons_list.append(t)
    # 3. Positive facts (order P1..P4)
    for t in positive_facts:
        if len(reasons_list) < 3 and t not in reasons_list:
            reasons_list.append(t)
    # 4. Newest non-official event labelled "খবরে প্রকাশিত, নিশ্চিত নয়"
    if len(reasons_list) < 3:
        for ev in events:
            if not ev.get("official") and ev.get("status") in {"reported", "alleged"}:
                ed = ev.get("event_date")
                reasons_list.append(Trigger(
                    rule_id="EV_UNOFFICIAL",
                    fact_or_event_id=ev.get("event_id"),
                    source_info=ev.get("source_info", {}),
                    text_bn=f"{ev.get('title_bn', '')} — খবরে প্রকাশিত, নিশ্চিত নয় ({format_date(ed, bn=True) if ed else ''})।",
                    text_en=f"{ev.get('title_en', '')} — reported, unconfirmed ({format_date(ed, bn=False) if ed else ''})."
                ))
                break

    # If still empty (nothing at all)
    if len(reasons_list) == 0:
        reasons_list.append(Trigger(
            rule_id="None",
            fact_or_event_id=None,
            source_info={},
            text_bn="সর্বশেষ তথ্যে বড় কোনো সতর্কতার সংকেত নেই।",
            text_en="No major warning signs in the latest data."
        ))

    # Build output reasons with source data
    formatted_reasons = []
    for r in reasons_list:
        check_forbidden_words(r.text_bn)
        check_forbidden_words(r.text_en)
        src = r.source_info or {}
        formatted_reasons.append({
            "rule": r.rule_id,
            "text_bn": r.text_bn,
            "text_en": r.text_en,
            "fact_id": r.fact_or_event_id,
            "source_url": src.get("url"),
            "source_title": src.get("title"),
            "published_at": str(src.get("published_at")) if src.get("published_at") else None,
            "page": src.get("page"),
            "quote": src.get("quote"),
            "checked": bool(src.get("checked"))
        })

    lbl_bn, lbl_en = STATUS_LABELS[status_code]
    return EvalResult(
        code=status_code,
        label_bn=lbl_bn,
        label_en=lbl_en,
        triggers=high_triggers + watch_triggers,
        reasons=formatted_reasons[:3],
        rules_version=rules_version
    )
