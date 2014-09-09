from django.contrib.auth.models import User
from django.test import TestCase

from bhr.models import BHRDB

# Create your tests here.

class DBTests(TestCase):
    def setUp(self):
        self.db = BHRDB()
        self.user = User.objects.create_user('admin', 'a@b.com', 'admin')

    def test_non_existing_block_is_none(self):
        b = self.db.get_block('1.2.3.4')
        self.assertEqual(b, None)

    def test_adding_a_block_works(self):
        b = self.db.add_block('1.2.3.4', self.user, 'test', 'testing')
        self.assertEqual(str(b.cidr), '1.2.3.4/32')

    def test_adding_a_block_twice_gets_the_same_block(self):
        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing')
        b2 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing')
        self.assertEqual(b1.id, b2.id)

    def test_blocking_changes_expected(self):
        expected = self.db.expected().all()
        self.assertEqual(len(expected), 0)

        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing')

        expected = self.db.expected().all()
        self.assertEqual(len(expected), 1)

    def test_blocking_does_not_change_current(self):
        current = self.db.current().all()
        self.assertEqual(len(current), 0)

        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing')

        current = self.db.current().all()
        self.assertEqual(len(current), 0)

    def test_block_entry_changes_current(self):
        current = self.db.current().all()
        self.assertEqual(len(current), 0)

        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing')
        self.db.set_blocked('1.2.3.4', 'bgp1')

        current = self.db.current().all()
        self.assertEqual(len(current), 1)

    def test_block_then_unblock_changes_current_but_not_expected(self):
        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing')
        self.db.set_blocked('1.2.3.4', 'bgp1')

        current = self.db.current().all()
        self.assertEqual(len(current), 1)

        self.db.set_unblocked('1.2.3.4', 'bgp1')

        current = self.db.current().all()
        self.assertEqual(len(current), 0)

        expected = self.db.expected().all()
        self.assertEqual(len(expected), 1)

    def test_block_queue_empty(self):
        q = self.db.block_queue('bgp1')
        self.assertEqual(len(q), 0)

    def test_block_queue(self):
        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing')

        q = self.db.block_queue('bgp1')

        self.assertEqual(len(q), 1)
        self.assertEqual(str(q[0].cidr), '1.2.3.4/32')

        self.db.set_blocked('1.2.3.4', 'bgp1')

        q = self.db.block_queue('bgp1')

        self.assertEqual(len(q), 0)

    def test_block_two_blockers(self):
        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing')

        for ident in 'bgp1', 'bgp2':
            q = self.db.block_queue(ident)
            self.assertEqual(len(q), 1)
            self.assertEqual(str(q[0].cidr), '1.2.3.4/32')

        self.db.set_blocked('1.2.3.4', 'bgp1')
        self.db.set_blocked('1.2.3.4', 'bgp2')

        for ident in 'bgp1', 'bgp2':
            q = self.db.block_queue(ident)
            self.assertEqual(len(q), 0)

    def test_block_two_blockers_only_one(self):
        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing')

        self.db.set_blocked('1.2.3.4', 'bgp1')

        q = self.db.block_queue('bgp1')
        self.assertEqual(len(q), 0)

        q = self.db.block_queue('bgp2')
        self.assertEqual(len(q), 1)

    def test_block_two_blockers_doesnt_double_current(self):
        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing')

        self.db.set_blocked('1.2.3.4', 'bgp1')
        self.db.set_blocked('1.2.3.4', 'bgp2')

        current = self.db.current().all()
        self.assertEqual(len(current), 1)

    def test_adding_a_block_adds_to_pending(self):
        pending = self.db.pending().all()
        self.assertEqual(len(pending), 0)

        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing')
        pending = self.db.pending().all()
        self.assertEqual(len(pending), 1)

    def test_blocking_removes_from_pending(self):
        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing')

        pending = self.db.pending().all()
        self.assertEqual(len(pending), 1)

        self.db.set_blocked('1.2.3.4', 'bgp1')

        pending = self.db.pending().all()
        self.assertEqual(len(pending), 0)
