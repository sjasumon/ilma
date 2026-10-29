"""Test startup explicitly uses the test environment; never production secrets."""
import os
os.environ.setdefault('ILMA_ENV','test')
