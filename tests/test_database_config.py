import unittest
from ilma_api.database_config import build_database_url

class TestDatabaseConfiguration(unittest.TestCase):
    def test_default_database_belongs_to_ilma(self):
        self.assertEqual(build_database_url({}).database, 'ilma')

    def test_separate_fields_reserved_password(self):
        password = 'p@ss:/#?% word'
        url = build_database_url({'DB_HOST':'db.internal', 'DB_PORT':'3306', 'DB_NAME':'ilma', 'DB_USERNAME':'builder', 'DB_PASSWORD':password})
        self.assertEqual(url.password, password)
        self.assertEqual(url.database, 'ilma')
        self.assertEqual(url.query['charset'], 'utf8mb4')
        self.assertEqual(url.drivername, 'mysql+pymysql')

    def test_mixed_case_aliases_and_old_url(self):
        url = build_database_url({'DB_username':'builder', 'DB_PASSWORD':'', 'db_pass':'secret', 'db_name':'ilma', 'DATABASE_URL':'old-invalid-value'})
        self.assertEqual(url.username, 'builder')
        self.assertEqual(url.password, 'secret')

    def test_url_still_supported(self):
        self.assertEqual(build_database_url({'DATABASE_URL':'mysql://user:pass@localhost/ilma'}).drivername, 'mysql+pymysql')

    def test_incomplete_and_invalid_config_never_prints_password(self):
        for config in [{'DB_USERNAME':'builder'}, {'DB_USERNAME':'builder', 'DB_NAME':'ilma', 'DB_PORT':'bad'}, {'DATABASE_URL':'sqlite:///test.db'}, {'DATABASE_URL':'not-a-url'}]:
            with self.assertRaises(ValueError): build_database_url(config)
