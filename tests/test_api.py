import unittest
from ilma_api.main import app, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from ilma_api.db import Base
from ilma_api import seed_loader
from unittest.mock import patch

class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(cls.engine)
        cls.sessions = sessionmaker(bind=cls.engine)
        with patch.object(seed_loader, "SessionLocal", cls.sessions):
            seed_loader.seed_data()

        def fixture_db():
            with cls.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = fixture_db

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        cls.engine.dispose()

    def setUp(self):
        self.db = self.sessions()

    def tearDown(self):
        self.db.close()

    def test_health(self):
        from ilma_api.main import health_check
        self.assertTrue(health_check(self.db)["ok"])

    def test_institutions_search(self):
        from ilma_api.main import search_institutions
        for query in ("ইস্টার্ন", "eastern", "EBL"):
            self.assertEqual(search_institutions(query, self.db)[0]["slug"], "eastern-bank")
        self.assertLessEqual(len(search_institutions(None, self.db)), 5)

    def test_report_card(self):
        from ilma_api.main import get_report_card
        data = get_report_card("101", self.db)
        self.assertEqual(data["institution"]["name_en"], "Eastern Bank PLC")
        self.assertNotIn("checks", data)
        self.assertLessEqual(len(data["reasons"]), 3)

    def test_services_endpoints(self):
        from ilma_api.main import calculate_insurance, calculate_return
        insurance = calculate_insurance(500000, "bank")
        self.assertEqual(insurance["insured"], 200000)
        self.assertEqual(insurance["uninsured"], 300000)
        result = calculate_return(100000, .085, 12, True)
        self.assertEqual(result["gross_interest"], 8500)
        self.assertEqual(result["tax_rate"], .10)

    def test_missing_institution_error(self):
        import json
        from ilma_api.main import get_report_card
        response = get_report_card("missing", self.db)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(json.loads(response.body)["error"]["code"], "not_found")

    def test_calculators_do_not_expose_personal_amount_routes(self):
        paths=app.openapi()['paths']
        self.assertNotIn('/v1/services/insurance-split',paths)
        self.assertNotIn('/v1/services/calculate-return',paths)

    def test_licence_only_has_no_status(self):
        from ilma_api.db import Institution
        from ilma_api.main import get_report_card
        self.db.add(Institution(id=999, slug="sample-licence-only", name_bn="নমুনা", name_en="Sample", type="bank", coverage="licence_only"))
        self.db.commit()
        self.assertIsNone(get_report_card("999", self.db)["status"])

if __name__ == "__main__":
    unittest.main()
