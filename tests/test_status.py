import unittest
from datetime import date
from decimal import Decimal
from ilma_api.rules.status import evaluate
from ilma_api.rules.reasons import check_forbidden_words

class TestStatusRules(unittest.TestCase):
    def test_forbidden_words(self):
        with self.assertRaises(ValueError):
            check_forbidden_words("ব্যাংকটি দেউলিয়া হয়ে গেছে")
        with self.assertRaises(ValueError):
            check_forbidden_words("ব্যাংকটি ডুবে যাচ্ছে")

    def test_strong_status(self):
        inst = {"id": 101, "slug": "test-bank", "name_bn": "টেস্ট ব্যাংক", "name_en": "Test Bank", "type": "bank", "islamic": False, "licensed": True, "listed": True, "coverage": "full"}
        data = {
            "facts": {
                "crar": {"fact_id": "f1", "value": 0.1549, "period": "2025", "period_end": date(2025, 12, 31), "source_info": {"title": "AR 2025"}},
                "npl_ratio": {"fact_id": "f2", "value": 0.0224, "period": "2025", "period_end": date(2025, 12, 31), "source_info": {"title": "AR 2025"}},
                "net_profit": {"fact_id": "f3", "value": 6000000000, "period": "2025", "period_end": date(2025, 12, 31), "source_info": {"title": "AR 2025"}},
            },
            "ratings": [
                {"fact_id": "r1", "agency": "CRAB", "long_term": "AAA", "rated_on": date(2026, 6, 1), "outlook": "stable", "source_info": {"title": "CRAB"}}
            ],
            "events": [],
            "rates": {},
            "median_12m_fdr": 0.08
        }
        res = evaluate(inst, data, as_of=date(2026, 10, 27))
        self.assertEqual(res.code, "strong")
        rules = [r["rule"] for r in res.reasons]
        self.assertIn("P1", rules)
        self.assertIn("P2", rules)

    def test_watch_npl(self):
        inst = {"id": 101, "slug": "test-bank", "type": "bank", "coverage": "full"}
        data = {
            "facts": {
                "crar": {"fact_id": "f1", "value": 0.14, "period": "2025", "period_end": date(2025, 12, 31), "source_info": {}},
                "npl_ratio": {"fact_id": "f2", "value": 0.18, "period": "2025", "period_end": date(2025, 12, 31), "source_info": {}}
            },
            "ratings": [],
            "events": [],
            "rates": {},
            "median_12m_fdr": 0.08
        }
        res = evaluate(inst, data, as_of=date(2026, 10, 27))
        self.assertEqual(res.code, "watch")
        self.assertEqual(res.reasons[0]["rule"], "W1")

    def test_developing_outlook_is_a_watch_reason(self):
        inst = {"id": 101, "slug": "test-bank", "type": "bank", "coverage": "full"}
        data = {
            "facts": {
                "crar": {"fact_id": "f1", "value": 0.14, "period": "2025", "period_end": date(2025, 12, 31), "source_info": {}},
                "npl_ratio": {"fact_id": "f2", "value": 0.03, "period": "2025", "period_end": date(2025, 12, 31), "basis": "solo_calculated", "source_info": {}}
            },
            "ratings": [{"fact_id": "r1", "agency": "CRISL", "long_term": "A", "rated_on": date(2026, 8, 25), "outlook": "developing", "source_info": {}}],
            "events": [], "rates": {}, "median_12m_fdr": 0.08
        }
        res = evaluate(inst, data, as_of=date(2026, 10, 27))
        self.assertEqual(res.code, "watch")
        self.assertEqual(res.reasons[0]["rule"], "W3")
        self.assertIn("পূর্বাভাস অনিশ্চিত", res.reasons[0]["text_bn"])
        self.assertNotIn("P3", [r["rule"] for r in res.reasons])

    def test_high_npl_and_crar(self):
        inst = {"id": 101, "slug": "test-bank", "type": "bank", "coverage": "full"}
        data = {
            "facts": {
                "crar": {"fact_id": "f1", "value": 0.08, "period": "2025", "period_end": date(2025, 12, 31), "source_info": {}},
                "npl_ratio": {"fact_id": "f2", "value": 0.26, "period": "2025", "period_end": date(2025, 12, 31), "source_info": {}}
            },
            "ratings": [],
            "events": [],
            "rates": {},
            "median_12m_fdr": 0.08
        }
        res = evaluate(inst, data, as_of=date(2026, 10, 27))
        self.assertEqual(res.code, "high")
        rules = [r["rule"] for r in res.reasons]
        self.assertEqual(rules[0], "H3")
        self.assertEqual(rules[1], "H4")

    def test_no_data_triggers(self):
        inst = {"id": 101, "slug": "test-bank", "type": "bank", "coverage": "full"}
        data = {
            "facts": {
                "crar": {"fact_id": "f1", "value": 0.15, "period": "2024", "period_end": date(2024, 12, 31), "source_info": {}},
                "npl_ratio": {"fact_id": "f2", "value": 0.03, "period": "2024", "period_end": date(2024, 12, 31), "source_info": {}}
            },
            "ratings": [],
            "events": [],
            "rates": {},
            "median_12m_fdr": 0.08
        }
        res = evaluate(inst, data, as_of=date(2026, 10, 27))
        self.assertEqual(res.code, "no_data")
        self.assertEqual(res.reasons[0]["rule"], "No data")

        data["events"] = [
            {"event_id": "e1", "type": "administrator", "official": True, "event_date": date(2026, 1, 10), "source_info": {}}
        ]
        res_high = evaluate(inst, data, as_of=date(2026, 10, 27))
        self.assertEqual(res_high.code, "high")
        self.assertEqual(res_high.reasons[0]["rule"], "H1")

    def test_future_event_does_not_trigger_high(self):
        inst = {"id": 101, "slug": "test-bank", "name_bn": "টেস্ট ব্যাংক", "name_en": "Test Bank", "type": "bank", "coverage": "full"}
        data = {
            "facts": {
                "crar": {"fact_id": "f1", "value": 0.15, "period": "2025", "period_end": date(2025, 12, 31), "source_info": {}},
                "npl_ratio": {"fact_id": "f2", "value": 0.03, "period": "2025", "period_end": date(2025, 12, 31), "source_info": {}},
            },
            "ratings": [],
            "events": [
                {"event_id": "e-future", "type": "administrator", "official": True, "event_date": date(2027, 5, 1), "source_info": {}},
            ],
            "rates": {},
            "median_12m_fdr": 0.08
        }
        res = evaluate(inst, data, as_of=date(2026, 10, 27))
        self.assertNotEqual(res.code, "high")
        self.assertNotIn("H1", [r["rule"] for r in res.reasons])

    def test_watch_w2_has_no_advice_word(self):
        inst = {"id": 101, "slug": "test-bank", "name_bn": "টেস্ট ব্যাংক", "name_en": "Test Bank", "type": "bank", "coverage": "full"}
        data = {
            "facts": {
                "crar": {"fact_id": "f1", "value": 0.11, "period": "2025", "period_end": date(2025, 12, 31), "source_info": {}},
                "npl_ratio": {"fact_id": "f2", "value": 0.03, "period": "2025", "period_end": date(2025, 12, 31), "source_info": {}},
            },
            "ratings": [],
            "events": [],
            "rates": {},
            "median_12m_fdr": 0.08
        }
        res = evaluate(inst, data, as_of=date(2026, 10, 27))
        self.assertEqual(res.code, "watch")
        for reason in res.reasons:
            self.assertNotIn("নিরাপদ", reason["text_bn"])
            self.assertNotIn("safe", reason["text_en"].lower())

    def test_missing_rules_version_is_loud(self):
        inst = {"id": 101, "slug": "test-bank", "type": "bank", "coverage": "full"}
        data = {"facts": {}, "ratings": [], "events": [], "rates": {}, "median_12m_fdr": 0.08}
        with self.assertRaises(KeyError):
            evaluate(inst, data, date(2026, 10, 27), cfg={"crar_min": 0.10})

if __name__ == "__main__":
    unittest.main()
