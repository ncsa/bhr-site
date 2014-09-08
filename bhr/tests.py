from django.test import TestCase

from bhr.models import BHRDB

# Create your tests here.

class DBTests(TestCase):
    def setUp(self):
        self.db = BHRDB()

    def test_non_existing_block_is_none(self):
        pass
