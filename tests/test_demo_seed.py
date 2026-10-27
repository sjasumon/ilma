import unittest
from pathlib import Path
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from ilma_api.csv_loader import load
from ilma_api.db import Fact,Event
from ilma_api.report_card import get_institution_report_card


class TestDemoSeed(unittest.TestCase):
    def test_both_converters_round_trip_handwritten_examples(self):
        import tempfile
        from ilma_api.export_seed import convert
        from ilma_api.export_seed import read
        source=Path(__file__).parent/'fixtures/sample_export'
        with tempfile.TemporaryDirectory() as output:
            codes={'EBL','BRACBANK','CITYBANK'}
            bank_data=convert(source,output,services=False,bank_codes=codes)
            service_data=convert(source,output,services=True,bank_codes=codes)
            self.assertEqual(len(bank_data['institution']),3)
            self.assertEqual(len(bank_data['fact']),9)
            self.assertEqual(len(bank_data['event']),0)
            self.assertEqual(len(service_data['service_offer']),6)
            self.assertEqual(len(read(Path(output)/'fact.csv')),9)
            self.assertEqual(len(read(Path(output)/'service_offer.csv')),6)
            self.assertEqual(bank_data['fact'][0]['value'],__import__('decimal').Decimal('.12'))
            self.assertIsNone(bank_data['source'][0]['published_at'])
            # A tiny synthetic fixture must never pass the production nine-bank gate.
            with self.assertRaises(ValueError): convert(source,output)

    def test_eight_strong_one_no_data_without_threshold_changes(self):
        engine=create_engine('sqlite://')
        statuses=load(Path(__file__).resolve().parents[1]/'seed',engine)
        self.assertEqual(list(statuses.values()).count('strong'),8)
        self.assertEqual(statuses['sbacbank'],'no_data')
        with Session(engine) as db:
            self.assertTrue(all(not row.official for row in db.scalars(select(Event))))
            self.assertEqual(db.scalar(select(Fact).where(Fact.institution_id==33,Fact.metric=='crar',Fact.period=='2025')).basis,'consolidated')
            card=get_institution_report_card(db,19)
            self.assertEqual(len(card['reasons']),3)
            self.assertTrue(all(reason['source_url'] and reason['quote'] for reason in card['reasons']))
            self.assertEqual(card['data_date'],'2025-12-31')
            from ilma_api.voice_facts import detail_facts
            self.assertEqual(detail_facts('fraud history',14,'en',db),[])
            self.assertTrue(detail_facts('news',14,'en',db))
            from ilma_api.main import get_banking_news
            news=get_banking_news(db)
            self.assertEqual(len(news),4)  # one story links both City and BRAC
            self.assertTrue(all(item['source_url'] and not item['official'] for item in news))
            self.assertTrue(all('not confirmed' in item['summary_en'] for item in news))
        engine.dispose()
