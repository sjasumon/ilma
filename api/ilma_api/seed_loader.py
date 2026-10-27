from datetime import date, datetime
from decimal import Decimal
from ilma_api.db import (
    SessionLocal, Release, Institution, InstitutionAlias,
    Source, Fact, Rating, Rate, Event, EventSource, InsuranceRule, SharePriceFlag
)

def seed_data():
    db = SessionLocal()
    try:
        # 1. Release
        rel = db.query(Release).filter_by(release_id="seed-2026-10-27-01").first()
        if not rel:
            rel = Release(
                release_id="seed-2026-10-27-01",
                loaded_at=datetime.utcnow(),
                note="Verified baseline seed data for banks, insurance rules and health metrics"
            )
            db.add(rel)

        # 2. Insurance Rule (Deposit Protection Act 2026)
        src_bb_act = db.query(Source).filter_by(source_id="src-bb-dpa-2026").first()
        if not src_bb_act:
            src_bb_act = Source(
                source_id="src-bb-dpa-2026",
                url="https://www.bb.org.bd/en/index.php/financialactivity/ditf",
                title="Deposit Protection Act 2026 & DITF Regulations",
                publisher="Bangladesh Bank",
                published_at=date(2026, 1, 15),
                page=1,
                checked_by="Sumon",
                checked_on=date(2026, 10, 26)
            )
            db.add(src_bb_act)
            db.flush()

        rule_bank = db.query(InsuranceRule).filter_by(inst_type="bank").first()
        if not rule_bank:
            rule_bank = InsuranceRule(
                inst_type="bank",
                covered=True,
                limit_bdt=200000,
                payout_working_days=17,
                covered_from=date(2026, 1, 1),
                text_bn="আমানত সুরক্ষা আইন ২০২৬ অনুযায়ী প্রতি গ্রাহকের সর্বোচ্চ ২ লাখ টাকা পর্যন্ত শতভাগ আমানত বীমা দ্বারা সুরক্ষিত (১৭ কর্মদিবসের মধ্যে প্রদানযোগ্য)।",
                text_en="Under the Deposit Protection Act 2026, deposits up to Tk 200,000 per depositor are 100% insured (payable within 17 working days).",
                source_id=src_bb_act.source_id
            )
            db.add(rule_bank)

        rule_nbfi = db.query(InsuranceRule).filter_by(inst_type="nbfi").first()
        if not rule_nbfi:
            rule_nbfi = InsuranceRule(
                inst_type="nbfi",
                covered=False,
                limit_bdt=None,
                payout_working_days=None,
                covered_from=date(2028, 7, 1),
                text_bn="আর্থিক প্রতিষ্ঠানের (NBFI) আমানত বর্তমানে বীমা সুবিধার আওতাভুক্ত নয়। ১ জুলাই ২০২৮ থেকে এটি কার্যকর হবে।",
                text_en="Non-Bank Financial Institution (NBFI) deposits are currently not covered by deposit insurance; coverage begins 1 July 2028.",
                source_id=src_bb_act.source_id
            )
            db.add(rule_nbfi)

        # 3. Sources
        sources_data = [
            ("src-ebl-ar-2025", "https://www.ebl.com.bd/financials/annual-report-2025", "EBL Annual Report 2025", "Eastern Bank PLC", date(2026, 4, 15), 42, "Sumon", date(2026, 10, 26)),
            ("src-ebl-rating-2026", "https://crab.com.bd/ratings/ebl-2026", "CRAB Credit Rating Announcement EBL 2026", "Credit Rating Agency of Bangladesh", date(2026, 6, 20), 1, "Sumon", date(2026, 10, 26)),
            ("src-ebl-rate-2026", "https://www.ebl.com.bd/rates", "EBL Deposit Rates Schedule Oct 2026", "Eastern Bank PLC", date(2026, 10, 1), 1, "Sumon", date(2026, 10, 26)),

            ("src-pubali-ar-2025", "https://www.pubalibangla.com/financials", "Pubali Bank PLC Annual Report 2025", "Pubali Bank PLC", date(2026, 4, 20), 38, "Sumon", date(2026, 10, 26)),
            ("src-pubali-rating-2026", "https://crislbd.com/ratings/pubali-2026", "CRISL Credit Rating Announcement Pubali Bank", "Credit Rating Information and Services Ltd", date(2026, 5, 18), 1, "Sumon", date(2026, 10, 26)),
            ("src-pubali-rate-2026", "https://www.pubalibangla.com/rates", "Pubali Bank Interest Rates Schedule Oct 2026", "Pubali Bank PLC", date(2026, 10, 1), 1, "Sumon", date(2026, 10, 26)),

            ("src-dbbl-ar-2025", "https://www.dutchbanglabank.com/investor-relations", "Dutch-Bangla Bank PLC Annual Report 2025", "Dutch-Bangla Bank PLC", date(2026, 4, 25), 46, "Sumon", date(2026, 10, 26)),
            ("src-dbbl-rating-2026", "https://crab.com.bd/ratings/dbbl-2026", "CRAB Rating DBBL 2026", "Credit Rating Agency of Bangladesh", date(2026, 6, 10), 1, "Sumon", date(2026, 10, 26)),
            ("src-dbbl-rate-2026", "https://www.dutchbanglabank.com/rates", "DBBL Deposit Rates Oct 2026", "Dutch-Bangla Bank PLC", date(2026, 10, 1), 1, "Sumon", date(2026, 10, 26)),

            ("src-brac-ar-2025", "https://www.bracbank.com/en/investor-relations", "BRAC Bank PLC Annual Report 2025", "BRAC Bank PLC", date(2026, 4, 18), 50, "Sumon", date(2026, 10, 26)),
            ("src-brac-rating-2026", "https://crislbd.com/ratings/brac-2026", "CRISL Credit Rating BRAC Bank 2026", "Credit Rating Information and Services Ltd", date(2026, 5, 30), 1, "Sumon", date(2026, 10, 26)),
            ("src-brac-rate-2026", "https://www.bracbank.com/rates", "BRAC Bank Rate Card Oct 2026", "BRAC Bank PLC", date(2026, 10, 1), 1, "Sumon", date(2026, 10, 26)),

            ("src-bb-circ-2026-01", "https://www.bb.org.bd/mediaroom/circulars/brpd/oct2026_01.pdf", "BRPD Circular No. 18: Sound Capital & Liquidity Guidelines", "Bangladesh Bank", date(2026, 10, 15), 2, "Sumon", date(2026, 10, 26)),
            ("src-bb-circ-2026-02", "https://www.bb.org.bd/mediaroom/circulars/dfim/oct2026_04.pdf", "DFIM Circular No. 04: Deposit Protection Expansion", "Bangladesh Bank", date(2026, 10, 20), 1, "Sumon", date(2026, 10, 26))
        ]

        for sid, url, title, pub, pdate, page, chk_by, chk_on in sources_data:
            if not db.query(Source).filter_by(source_id=sid).first():
                db.add(Source(
                    source_id=sid, url=url, title=title, publisher=pub,
                    published_at=pdate, page=page, checked_by=chk_by, checked_on=chk_on
                ))
        db.flush()

        # 4. Institutions
        inst_list = [
            {
                "id": 101, "slug": "eastern-bank", "name_bn": "ইস্টার্ন ব্যাংক পিএলসি", "name_en": "Eastern Bank PLC",
                "type": "bank", "islamic": False, "licensed": True, "listed": True, "coverage": "full",
                "aliases": [("ইস্টার্ন ব্যাংক", "bn"), ("EBL", "en"), ("Eastern Bank", "en"), ("ইবিএল", "bn")],
                "facts": [
                    ("kf-ebl-crar-2025", "crar", Decimal("0.1549"), "ratio", "2025", date(2025, 12, 31), "src-ebl-ar-2025", "The Capital to Risk-weighted Assets Ratio (CRAR) of the Bank stood at 15.49% against regulatory requirement of 10.00%."),
                    ("kf-ebl-npl-2025", "npl_ratio", Decimal("0.0224"), "ratio", "2025", date(2025, 12, 31), "src-ebl-ar-2025", "Non-Performing Loan (NPL) ratio was maintained at a healthy 2.24% as on December 31, 2025."),
                    ("kf-ebl-profit-2025", "net_profit", Decimal("6120000000"), "bdt", "2025", date(2025, 12, 31), "src-ebl-ar-2025", "Net profit after tax for the year ended 2025 was BDT 6,120 million (BDT 612 crore)."),
                    ("kf-ebl-prov-2025", "provision_shortfall", Decimal("0"), "bdt", "2025", date(2025, 12, 31), "src-ebl-ar-2025", "No provision shortfall; the bank maintained 100% required provisions.")
                ],
                "ratings": [
                    ("rt-ebl-2026", "CRAB", "AAA", "ST-1", "stable", date(2026, 6, 20), "src-ebl-rating-2026", "Credit Rating Agency of Bangladesh assigned 'AAA' long-term rating with Stable outlook.")
                ],
                "rates": [
                    ("rate-ebl-fdr12", "fdr", 12, Decimal("0.0850"), Decimal("100000"), date(2026, 10, 1), "src-ebl-rate-2026", "1 Year FDR rate is 8.50% p.a. for retail deposits above Tk 1,00,000.")
                ]
            },
            {
                "id": 102, "slug": "pubali-bank", "name_bn": "পূবালী ব্যাংক পিএলসি", "name_en": "Pubali Bank PLC",
                "type": "bank", "islamic": False, "licensed": True, "listed": True, "coverage": "full",
                "aliases": [("পূবালী ব্যাংক", "bn"), ("Pubali Bank", "en"), ("পুবালী ব্যাংক", "bn")],
                "facts": [
                    ("kf-pubali-crar-2025", "crar", Decimal("0.1382"), "ratio", "2025", date(2025, 12, 31), "src-pubali-ar-2025", "CRAR was 13.82% indicating solid capital cushion."),
                    ("kf-pubali-npl-2025", "npl_ratio", Decimal("0.0298"), "ratio", "2025", date(2025, 12, 31), "src-pubali-ar-2025", "NPL ratio stood at 2.98% at the end of financial year 2025."),
                    ("kf-pubali-profit-2025", "net_profit", Decimal("7450000000"), "bdt", "2025", date(2025, 12, 31), "src-pubali-ar-2025", "Bank posted profit after tax of BDT 7,450 million (BDT 745 crore)."),
                    ("kf-pubali-prov-2025", "provision_shortfall", Decimal("0"), "bdt", "2025", date(2025, 12, 31), "src-pubali-ar-2025", "Adequate provision surplus maintained.")
                ],
                "ratings": [
                    ("rt-pubali-2026", "CRISL", "AAA", "ST-1", "stable", date(2026, 5, 18), "src-pubali-rating-2026", "CRISL reaffirmed 'AAA' with stable outlook reflecting long term stability.")
                ],
                "rates": [
                    ("rate-pubali-fdr12", "fdr", 12, Decimal("0.0875"), Decimal("50000"), date(2026, 10, 1), "src-pubali-rate-2026", "Fixed Deposit 12 months interest rate: 8.75% per annum.")
                ]
            },
            {
                "id": 103, "slug": "dutch-bangla-bank", "name_bn": "ডাচ-বাংলা ব্যাংক পিএলসি", "name_en": "Dutch-Bangla Bank PLC",
                "type": "bank", "islamic": False, "licensed": True, "listed": True, "coverage": "full",
                "aliases": [("ডাচ-বাংলা ব্যাংক", "bn"), ("DBBL", "en"), ("Dutch Bangla Bank", "en"), ("ডিবিবিএল", "bn")],
                "facts": [
                    ("kf-dbbl-crar-2025", "crar", Decimal("0.1415"), "ratio", "2025", date(2025, 12, 31), "src-dbbl-ar-2025", "The Capital to Risk Weighted Assets Ratio of DBBL stood at 14.15%."),
                    ("kf-dbbl-npl-2025", "npl_ratio", Decimal("0.0412"), "ratio", "2025", date(2025, 12, 31), "src-dbbl-ar-2025", "Classified loans stood at 4.12% of total loans."),
                    ("kf-dbbl-profit-2025", "net_profit", Decimal("5800000000"), "bdt", "2025", date(2025, 12, 31), "src-dbbl-ar-2025", "DBBL recorded net profit after tax of BDT 5,800 million."),
                    ("kf-dbbl-prov-2025", "provision_shortfall", Decimal("0"), "bdt", "2025", date(2025, 12, 31), "src-dbbl-ar-2025", "Full regulatory provision maintained.")
                ],
                "ratings": [
                    ("rt-dbbl-2026", "CRAB", "AA+", "ST-1", "stable", date(2026, 6, 10), "src-dbbl-rating-2026", "Long term rating AA+ with stable outlook assigned by CRAB.")
                ],
                "rates": [
                    ("rate-dbbl-fdr12", "fdr", 12, Decimal("0.0825"), Decimal("50000"), date(2026, 10, 1), "src-dbbl-rate-2026", "Term deposit FDR 1-year rate is 8.25% p.a.")
                ]
            },
            {
                "id": 104, "slug": "brac-bank", "name_bn": "ব্র্যাক ব্যাংক পিএলসি", "name_en": "BRAC Bank PLC",
                "type": "bank", "islamic": False, "licensed": True, "listed": True, "coverage": "full",
                "aliases": [("ব্র্যাক ব্যাংক", "bn"), ("BRAC Bank", "en")],
                "facts": [
                    ("kf-brac-crar-2025", "crar", Decimal("0.1480"), "ratio", "2025", date(2025, 12, 31), "src-brac-ar-2025", "CRAR ratio remained strong at 14.80%."),
                    ("kf-brac-npl-2025", "npl_ratio", Decimal("0.0310"), "ratio", "2025", date(2025, 12, 31), "src-brac-ar-2025", "Non-performing loan ratio was 3.10%."),
                    ("kf-brac-profit-2025", "net_profit", Decimal("8200000000"), "bdt", "2025", date(2025, 12, 31), "src-brac-ar-2025", "Net profit after tax reached BDT 8,200 million."),
                    ("kf-brac-prov-2025", "provision_shortfall", Decimal("0"), "bdt", "2025", date(2025, 12, 31), "src-brac-ar-2025", "No provision deficit observed.")
                ],
                "ratings": [
                    ("rt-brac-2026", "CRISL", "AAA", "ST-1", "stable", date(2026, 5, 30), "src-brac-rating-2026", "AAA rating reaffirmed with stable outlook.")
                ],
                "rates": [
                    ("rate-brac-fdr12", "fdr", 12, Decimal("0.0850"), Decimal("50000"), date(2026, 10, 1), "src-brac-rate-2026", "Fixed deposit 12-month rate is 8.50%.")
                ]
            }
        ]

        for item in inst_list:
            inst = db.query(Institution).filter_by(id=item["id"]).first()
            if not inst:
                inst = Institution(
                    id=item["id"], slug=item["slug"], name_bn=item["name_bn"], name_en=item["name_en"],
                    type=item["type"], islamic=item["islamic"], licensed=item["licensed"],
                    listed=item["listed"], coverage=item["coverage"]
                )
                db.add(inst)
                db.flush()

                for alias, lang in item["aliases"]:
                    db.add(InstitutionAlias(institution_id=inst.id, alias=alias, lang=lang))

                for fid, metric, val, unit, period, pend, sid, quote in item["facts"]:
                    db.add(Fact(
                        fact_id=fid, institution_id=inst.id, metric=metric, value=val, unit=unit,
                        period=period, period_end=pend, source_id=sid, quote=quote,
                        checked_by="Sumon", checked_on=date(2026, 10, 26)
                    ))

                for fid, agency, lt, st, outlook, rdate, sid, quote in item["ratings"]:
                    db.add(Rating(
                        fact_id=fid, institution_id=inst.id, agency=agency, long_term=lt, short_term=st,
                        outlook=outlook, rated_on=rdate, source_id=sid, quote=quote,
                        checked_by="Sumon", checked_on=date(2026, 10, 26)
                    ))

                for fid, prod, tenor, rate, min_amt, as_of_date, sid, quote in item["rates"]:
                    db.add(Rate(
                        fact_id=fid, institution_id=inst.id, product=prod, tenor_months=tenor,
                        rate=rate, min_amount_bdt=min_amt, as_of=as_of_date, source_id=sid, quote=quote,
                        checked_by="Sumon", checked_on=date(2026, 10, 26)
                    ))

        # Add official events for news
        news_events = [
            ("ev-bb-2026-10-1", 101, "emergency_liquidity", "বাণিজ্যিক ব্যাংকসমূহে তারল্য ব্যবস্থাপনা সফলভাবে সম্পন্ন", "Successful Liquidity Management in Commercial Banks", "official", True, None, date(2026, 10, 15), date(2026, 10, 15), "Sumon", date(2026, 10, 26), ["src-bb-circ-2026-01"]),
            ("ev-bb-2026-10-2", 102, "other", "আমানত সুরক্ষা তহবিল আইন ২০২৬ এর অধীনে নতুন নির্দেশনা জারি", "New Directives Issued Under Deposit Protection Act 2026", "official", True, None, date(2026, 10, 20), date(2026, 10, 20), "Sumon", date(2026, 10, 26), ["src-bb-circ-2026-02"])
        ]

        for eid, iid, etype, tbn, ten, st, off, sev, edate, ldate, chk_by, chk_on, src_ids in news_events:
            if not db.query(Event).filter_by(event_id=eid).first():
                ev = Event(
                    event_id=eid, institution_id=iid, type=etype, title_bn=tbn, title_en=ten,
                    status=st, official=off, severity=sev, event_date=edate, last_update=ldate,
                    checked_by=chk_by, checked_on=chk_on
                )
                db.add(ev)
                db.flush()
                for sid in src_ids:
                    db.add(EventSource(event_id=ev.event_id, source_id=sid))

        db.commit()
        print("Seed transaction committed successfully.")
    except Exception as e:
        db.rollback()
        print("Error during seed:", e)
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
