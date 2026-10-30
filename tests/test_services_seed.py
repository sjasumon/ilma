import json
import unittest
from pathlib import Path
from decimal import Decimal
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from ilma_api.csv_loader import load
from ilma_api.db import ServiceOffer, Fact, Event
from ilma_api.export_seed import quote_numbers
from ilma_api.main import app, get_db
from ilma_api.voice_text import VoiceIntent, VoiceContext
from ilma_api.bank_services import voice_service_result


class TestServicesSeed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
        cls.directory=Path(__file__).resolve().parents[1]/'seed'
        cls.statuses=load(cls.directory,cls.engine)
        def fixture():
            with Session(cls.engine) as db:yield db
        app.dependency_overrides[get_db]=fixture
        cls.client=TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear();cls.client.close();cls.engine.dispose()

    def test_606_sourced_offers_and_literal_numeric_evidence(self):
        with Session(self.engine) as db:
            rows=db.scalars(select(ServiceOffer)).all()
            self.assertEqual(len(rows),606)
            for row in rows:
                self.assertTrue(row.source_url and row.page and row.quote)
                if row.value_num is not None:
                    if row.value_text.casefold()=='free':
                        self.assertEqual(row.value_num,0);self.assertIn('free',row.quote.casefold())
                    else:self.assertIn(row.value_num,quote_numbers(row.quote))

    def test_signature_exact_values_hidden_and_stale(self):
        response=self.client.get('/v1/services/compare',params=dict(product_type='card',network='Visa',tier='Signature'))
        self.assertEqual(response.status_code,200)
        rows={row['slug']:row for row in response.json()['rows']}
        self.assertEqual(len(rows),9)
        self.assertEqual([rows[key]['offer']['value_num'] for key in ['nccbank','bankasia','mtb','dutchbangl']],[7000,7000,12000,20000])
        self.assertTrue(rows['dutchbangl']['offer']['stale'])
        self.assertEqual(rows['bracbank']['offer']['value_num'],10000)
        self.assertEqual(rows['ebl']['offer']['value_num'],10000)
        self.assertIn('Signature Light / Women Signature',rows['ebl']['offer']['column_header'])
        self.assertEqual([v['value_num'] for v in rows['ebl']['alternatives']],[12000])
        self.assertEqual(rows['primebank']['state'],'checking')
        self.assertNotIn('offer',rows['primebank'])
        fresh=[r['offer']['value_num'] for r in rows.values() if r.get('offer') and not r['offer']['stale']]
        self.assertEqual(max(fresh)-min(fresh),5000)

    def test_fdr_twelve_months_is_like_for_like(self):
        rows={r['slug']:r for r in self.client.get('/v1/services/compare?product_type=fdr&tenor_months=12').json()['rows']}
        self.assertEqual(rows['citybank']['state'],'checking')
        self.assertEqual(rows['dutchbangl']['state'],'not_published')
        self.assertEqual(rows['ebl']['offer']['value_num'],6.5)
        self.assertEqual(rows['ebl']['offer']['product'],'Fixed Deposit 12 Months')
        self.assertTrue(all(row['offer']['tenor_months']==12 for row in rows.values() if row.get('offer')))
        charges=self.client.get('/v1/services/compare?product_type=account_fee&attribute=maintenance_fee_half_yearly').json()['rows']
        self.assertEqual(charges[0]['slug'],'bracbank')
        self.assertIn('Free',charges[0]['offer']['quote'])

    def test_hidden_offers_cannot_be_fetched_or_listed(self):
        with Session(self.engine) as db:
            hidden=db.scalars(select(ServiceOffer).where(ServiceOffer.hidden==True)).all()
            ids={row.offer_id for row in hidden}
            for row in hidden[:3]:self.assertEqual(self.client.get('/v1/services/offers/'+row.offer_id).status_code,404)
            for bank in {row.institution_id for row in hidden}:
                offers=self.client.get(f'/v1/institutions/{bank}/services').json()['offers']
                self.assertFalse(ids & {row['offer_id'] for row in offers})

    def test_calculator_amount_is_refused_by_server(self):
        self.assertEqual(self.client.get('/v1/services/compare?product_type=fdr&tenor_months=12&amount=100000').status_code,422)
        self.assertEqual(self.client.post('/v1/services/readout',json={'product_type':'fdr','amount':100000}).status_code,422)
        self.assertEqual(self.client.get('/v1/services/compare?product_type=card').status_code,422)

    def test_comparison_readout_has_no_runtime_provider_calls(self):
        from unittest.mock import patch, AsyncMock
        with patch('ilma_api.audio_cache.register_speech',new=AsyncMock(side_effect=AssertionError('No runtime TTS'))) as speak, patch('httpx.AsyncClient.post',new=AsyncMock(side_effect=AssertionError('No provider HTTP'))) as http, patch('ilma_api.service_clips.manifest',return_value={'version':1,'clips':{}}):
            response=self.client.post('/v1/services/readout',json=dict(product_type='card',network='Visa',tier='Gold',language='bn'))
        self.assertEqual(response.status_code,200)
        speak.assert_not_awaited();http.assert_not_awaited()
        self.assertIsNone(response.json()['audio_url'])
        spoken=response.json()['text']
        self.assertIn('ভিসা গোল্ড',spoken)
        self.assertNotIn('ডাচ্ বাংলা',spoken)
        self.assertNotIn('সেরা',spoken)
        self.assertIn('নগদ তোলার ফি দুই শতাংশ অথবা একশো পঞ্চাশ টাকা, যেটি বেশি।',spoken)
        self.assertNotIn('একশো পঞ্চাশ শতাংশ',spoken)

    def test_audio_manifest_is_not_cached_by_the_cdn(self):
        response=self.client.get('/v1/services/audio-manifest')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.headers['cache-control'],'no-store')
        self.assertIn('clips',response.json())

    def test_services_voice_navigates_to_signature_comparison(self):
        with Session(self.engine) as db:
            result=voice_service_result('সিগনেচার কার্ডের ফি',VoiceIntent(intent='rates',product='credit_card'),VoiceContext(tab='services'),db,'bn')
        self.assertEqual(result['comparison']['network'],'Visa')
        self.assertEqual(result['comparison']['tier'],'Signature')
        self.assertTrue(result['sources'])
        self.assertIn('১০,০০০',result['card_text'])
        self.assertIn('৭০০০',result['speech_text'])
        self.assertIn('১০,০০০',result['card_text'])
        self.assertNotIn('১২০০০',result['speech_text'])
        self.assertNotIn('২০০০০',result['speech_text'])
        self.assertEqual(result['speech_text'],result['text']);self.assertTrue(result['card_text'])
        with Session(self.engine) as db:
            sms=voice_service_result('SMS alert fees',VoiceIntent(intent='service_compare',product='account_fee',service_attribute='sms_alert_fee'),VoiceContext(tab='services'),db,'en')
        self.assertEqual(sms['comparison']['product_type'],'account_fee')
        self.assertEqual(sms['comparison']['attribute'],'sms_alert_fee')

    def test_service_rates_intent_without_bank_still_opens_comparison(self):
        import asyncio
        from unittest.mock import patch, AsyncMock
        from ilma_api.voice_pipeline import run_pipeline
        from ilma_api.main import get_institution_index
        async def check():
            with Session(self.engine) as db:
                with patch('ilma_api.voice_pipeline.understand',new=AsyncMock(return_value=VoiceIntent(intent='rates',product='credit_card',card_tier='signature'))):
                    return ''.join([chunk async for chunk in run_pipeline(None,'সিগনেচার কার্ডের ফি','',VoiceContext(tab='services',speak=False),get_institution_index(db),db,mode='text')])
        result=asyncio.run(check())
        self.assertIn('"tier": "Signature"',result)
        self.assertIn('"type": "service_answer"',result)
        self.assertNotIn('"type": "clarify"',result)

    def test_watch_persists_in_mysql_model_and_is_idempotent(self):
        headers={'X-ILMA-Device':'test-anonymous-device-12345678'}
        path='/v1/institutions/19/watch'
        self.assertTrue(self.client.post(path,headers=headers).json()['watching'])
        self.assertTrue(self.client.post(path,headers=headers).json()['watching'])
        self.assertTrue(self.client.get(path,headers=headers).json()['watching'])
        self.assertFalse(self.client.delete(path,headers=headers).json()['watching'])

    def test_import_is_idempotent(self):
        self.assertEqual(load(self.directory,self.engine),self.statuses)
        with Session(self.engine) as db:self.assertEqual(db.scalar(select(func.count()).select_from(ServiceOffer)),606)

    def test_duplicate_fact_rejects_whole_import(self):
        import tempfile,shutil,csv
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)
            for source in self.directory.glob('*.csv'):shutil.copy2(source,folder/source.name)
            shutil.copy2(self.directory/'release.json',folder/'release.json')
            with (folder/'fact.csv').open(encoding='utf-8',newline='') as source:
                reader=csv.DictReader(source);rows=list(reader);columns=reader.fieldnames
            with (folder/'fact.csv').open('a',encoding='utf-8',newline='') as output:csv.DictWriter(output,fieldnames=columns).writerow(rows[0])
            with self.assertRaisesRegex(ValueError,'duplicate'):load(folder,self.engine)
        with Session(self.engine) as db:self.assertEqual(db.scalar(select(func.count()).select_from(ServiceOffer)),606)

    def test_import_cannot_target_an_unrelated_mysql_database(self):
        from ilma_api.csv_loader import prepare_schema
        unrelated=create_engine('mysql+pymysql://localhost/project_db')
        with self.assertRaisesRegex(ValueError,'ilma database'):prepare_schema(unrelated)
        unrelated.dispose()

    def test_platinum_main_and_retail_variants_only(self):
        result=self.client.get('/v1/services/compare',params=dict(product_type='card',network='Visa',tier='Platinum')).json()
        rows={r['slug']:r for r in result['rows']}
        brac=rows['bracbank']
        self.assertEqual(brac['offer']['value_num'],5000)
        self.assertEqual(brac['offer']['column_header'],'Platinum')
        self.assertEqual({r['column_header']:r['value_num'] for r in brac['alternatives']},
                         {'Platinum Flexi':3000,'TARA Platinum':2500})
        self.assertTrue(all(r['variant']=='variant' for r in brac['alternatives']))
        self.assertEqual(rows['ebl']['offer']['value_num'],5000)
        self.assertEqual(len(rows['ebl']['alternatives']),1)
        listed=[r for b in result['rows'] for r in [b.get('offer'),*b.get('alternatives',[])] if r]
        self.assertFalse(any(r['variant']=='excluded' for r in listed))
        # Excluded cards are inspectable only in the bank's own product view.
        bank=self.client.get('/v1/institutions/11/services').json()
        excluded=next(r for r in bank['offers'] if r['variant']=='excluded' and 'Corporate' in r['product'])
        detail=self.client.get('/v1/services/offers/'+excluded['offer_id']).json()
        self.assertTrue(detail['offers'])
        self.assertTrue(all(r['column_header']==excluded['column_header'] for r in detail['offers']))

    def test_handwritten_variant_order_is_independent_of_fee_and_input_order(self):
        from ilma_api.export_seed import card_variants
        def row(identifier,header,column,value='100',product=None):
            return dict(id=identifier,bank_id='SYNTHETIC',category='card',network='Visa',tier='Platinum',
                        basis='conventional',product=product or header,column_header=header,col_num=str(column),value=value)
        rows=[row('flexi','Platinum Flexi',1,'10'),row('main','প্লাটিনাম Platinum',5),
              row('corporate','Corporate Platinum',0),row('currency','Dollar Platinum',2,'US$ 30'),
              row('currency-rate','Dollar Platinum',2,'5')]
        result=card_variants(rows)
        self.assertEqual(result['main'],'main')
        self.assertEqual(result['flexi'],'variant')
        self.assertEqual(result['currency-rate'],'excluded')
        self.assertEqual(result['corporate'],'excluded')
        self.assertEqual(result,card_variants(list(reversed(rows))))
        rows=[row('later','Platinum Premium',9,'10'),row('entry','Platinum Entry',2,'100')]
        self.assertEqual(card_variants(rows),{'later':'variant','entry':'main'})

    def test_hidden_zero_and_text_notes_cannot_enter_retail_comparison(self):
        with Session(self.engine) as db:
            # Locate by content rather than depending on an input-row ID.
            zero=db.query(ServiceOffer).filter(ServiceOffer.product.contains('ZERO')).one()
            self.assertEqual(zero.value_num,0)
            self.assertTrue(zero.hidden)
            note=db.query(ServiceOffer).filter(ServiceOffer.value_text.contains('নোট ১৭')).one()
            self.assertIsNone(note.value_num)
            self.assertEqual(note.variant,'excluded')
            zero_id,note_id=zero.offer_id,note.offer_id
        self.assertEqual(self.client.get('/v1/services/offers/'+zero_id).status_code,404)
        detail=self.client.get('/v1/services/offers/'+note_id).json()
        self.assertEqual(detail['offers'][0]['value_text'],'নোট ১৭ অনুযায়ী')
