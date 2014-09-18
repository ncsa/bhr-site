from django.contrib.auth.models import User
from django.test import TestCase
import json
import csv

from bhr.models import BHRDB, WhitelistEntry

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
        self.db.set_blocked(b1, 'bgp1')

        current = self.db.current().all()
        self.assertEqual(len(current), 1)

    def test_block_then_unblock_changes_current_but_not_expected(self):
        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing')
        self.db.set_blocked(b1, 'bgp1')

        current = self.db.current().all()
        self.assertEqual(len(current), 1)

        self.db.set_unblocked(b1, 'bgp1')

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

        self.db.set_blocked(b1, 'bgp1')

        q = self.db.block_queue('bgp1')

        self.assertEqual(len(q), 0)

    def test_block_two_blockers(self):
        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing')

        for ident in 'bgp1', 'bgp2':
            q = self.db.block_queue(ident)
            self.assertEqual(len(q), 1)
            self.assertEqual(str(q[0].cidr), '1.2.3.4/32')

        self.db.set_blocked(b1, 'bgp1')
        self.db.set_blocked(b1, 'bgp2')

        for ident in 'bgp1', 'bgp2':
            q = self.db.block_queue(ident)
            self.assertEqual(len(q), 0)

    def test_block_two_blockers_only_one(self):
        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing')

        self.db.set_blocked(b1, 'bgp1')

        q = self.db.block_queue('bgp1')
        self.assertEqual(len(q), 0)

        q = self.db.block_queue('bgp2')
        self.assertEqual(len(q), 1)

    def test_block_two_blockers_doesnt_double_current(self):
        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing')

        self.db.set_blocked(b1, 'bgp1')
        self.db.set_blocked(b1, 'bgp2')

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

        self.db.set_blocked(b1, 'bgp1')

        pending = self.db.pending().all()
        self.assertEqual(len(pending), 0)

    def test_unblock_now_removes_from_expected(self):
        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing')

        expected = self.db.expected().all()
        self.assertEqual(len(expected), 1)

        self.db.unblock_now('1.2.3.4', 'testing')

        expected = self.db.expected().all()
        self.assertEqual(len(expected), 0)

    def test_unblock_now_moves_to_pending_removal(self):
        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing')
        self.db.unblock_now('1.2.3.4', 'testing')

        #it needs to be blocked on a host to be able to be pending unblock
        self.db.set_blocked(b1, 'bgp1')

        pending_removal = self.db.pending_removal().all()
        self.assertEqual(len(pending_removal), 1)

    def test_unblock_queue_empty(self):
        q = self.db.unblock_queue('bgp1')
        self.assertEqual(len(q), 0)

    def test_unblock_queue_empty_before_expiration(self):
        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing', duration=30)
        self.db.set_blocked(b1, 'bgp1')

        q = self.db.unblock_queue('bgp1')
        self.assertEqual(len(q), 0)

    def test_unblock_now_adds_to_unblock_queue(self):
        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing', duration=1)
        self.db.set_blocked(b1, 'bgp1')

        self.db.unblock_now('1.2.3.4', 'testing')

        q = self.db.unblock_queue('bgp1')
        self.assertEqual(len(q), 1)

    def test_unblock_queue_exists_after_expiration(self):
        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing', duration=1)
        self.db.set_blocked(b1, 'bgp1')
        sleep(2)
        q = self.db.unblock_queue('bgp1')
        self.assertEqual(len(q), 1)

    def test_set_unblocked_removes_from_unblock_queue(self):
        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing')
        self.db.set_blocked(b1, 'bgp1')
        self.db.unblock_now('1.2.3.4', 'testing')

        q = self.db.unblock_queue('bgp1')
        self.assertEqual(len(q), 1)

        self.db.set_unblocked(b1, 'bgp1')

        q = self.db.unblock_queue('bgp1')
        self.assertEqual(len(q), 0)

    def test_stats(self):
        def check_counts(block_pending=0, unblock_pending=0, current=0, expected=0):
            stats = self.db.stats()
            self.assertEqual(stats["block_pending"], block_pending)
            self.assertEqual(stats["unblock_pending"], unblock_pending)
            self.assertEqual(stats["current"], current)
            self.assertEqual(stats["expected"], expected)

        check_counts()

        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing')
        check_counts(block_pending=1, expected=1)

        self.db.set_blocked(b1, 'bgp1')
        check_counts(current=1, expected=1)

        self.db.unblock_now('1.2.3.4', 'testing')
        check_counts(current=1, expected=0, unblock_pending=1)

        self.db.set_unblocked(b1, 'bgp1')
        check_counts()

from rest_framework.test import APITestCase
from rest_framework import status
from time import sleep

class ApiTest(TestCase):
    def setUp(self):
        self.user = user = User.objects.create_user('admin', 'temporary@gmail.com', 'admin')
        self.client.login(username='admin', password='admin')

    def _add_block(self, cidr='1.2.3.4', duration=30, skip_whitelist=0):
        return self.client.post('/bhr/api/block', dict(
            cidr=cidr,
            source='test',
            why='testing',
            duration=duration,
            skip_whitelist=skip_whitelist
            ))

    def test_block(self):
        response = self._add_block()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_block_twice_returns_the_same_block(self):
        r1 = self._add_block().data
        r2 = self._add_block().data
        self.assertEqual(r1['url'], r2['url'])

    def test_block_skip_whitelist(self):
        WhitelistEntry(who=self.user, why='test', cidr='1.2.3.0/24').save()
        response = self._add_block()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self._add_block(skip_whitelist=True)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_block_queue(self):
        data = self.client.get("/bhr/api/queue/bgp1").data
        self.assertEqual(len(data), 0)
        self._add_block()

        data = self.client.get("/bhr/api/queue/bgp1").data
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['cidr'], '1.2.3.4/32')

    def test_unblock_queue(self):
        data = self.client.get("/bhr/api/unblock_queue/bgp1").data
        self.assertEqual(len(data), 0)
        block = self._add_block(duration=1).data
        self.client.post(block['set_blocked'], dict(ident='bgp1'))
        sleep(2)

        data = self.client.get("/bhr/api/unblock_queue/bgp1").data
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['block']['cidr'], '1.2.3.4/32')

    def test_set_blocked(self):
        self._add_block()

        block = self.client.get("/bhr/api/queue/bgp1").data[0]
        self.client.post(block['set_blocked'], dict(ident='bgp1'))

        data = self.client.get("/bhr/api/queue/bgp1").data
        self.assertEqual(len(data), 0)

    def test_block_queue_with_two_blockers(self):
        self._add_block()

        block = self.client.get("/bhr/api/queue/bgp1").data[0]
        self.client.post(block['set_blocked'], dict(ident='bgp1'))

        block = self.client.get("/bhr/api/queue/bgp2").data[0]
        self.client.post(block['set_blocked'], dict(ident='bgp2'))

        for ident in 'bgp1', 'bgp2':
            data = self.client.get("/bhr/api/queue/" + ident).data
            self.assertEqual(len(data), 0)

    def test_pending_blocks(self):
        self._add_block()

        block = self.client.get("/bhr/api/queue/bgp1").data[0]

        data = self.client.get("/bhr/api/pending_blocks/").data
        self.assertEqual(data[0]['cidr'], '1.2.3.4/32')

        self.client.post(block['set_blocked'], dict(ident='bgp1'))

        data = self.client.get("/bhr/api/pending_blocks/").data
        self.assertEqual(len(data), 0)

    def test_current_blocks(self):
        self._add_block()

        block = self.client.get("/bhr/api/queue/bgp1").data[0]

        data = self.client.get("/bhr/api/current_blocks/").data
        self.assertEqual(len(data), 0)

        self.client.post(block['set_blocked'], dict(ident='bgp1'))

        data = self.client.get("/bhr/api/current_blocks/").data
        self.assertEqual(data[0]['cidr'], '1.2.3.4/32')

    def test_history(self):
        hist = self.client.get("/bhr/api/query/1.2.3.4").data
        self.assertEqual(len(hist), 0)
        self._add_block()

        hist = self.client.get("/bhr/api/query/1.2.3.4").data
        self.assertEqual(len(hist), 1)


    def test_history_multiple(self):
        hist = self.client.get("/bhr/api/query/1.2.3.4").data
        self.assertEqual(len(hist), 0)
        self._add_block(duration=1)
        sleep(2)
        self._add_block(duration=1)

        hist = self.client.get("/bhr/api/query/1.2.3.4").data
        self.assertEqual(len(hist), 2)

    def test_all_in_one(self):
        """Test everything.  Not so useful if things fail, but useful to see how things work"""

        def check(which, cnt):
            data = self.client.get("/bhr/api/%s_blocks/" % which).data
            self.assertEqual(len(data), cnt, which)

        def check_counts(pending=0, current=0, expected=0):
            check("pending", pending)
            check("current", current)
            check("expected", expected)

        # at first, there is noting pending or blocked, and no queue.
        check_counts(0)

        #add a single block that expires in 10 seconds
        self._add_block(duration=3)

        #verify that it shows up in expected
        check_counts(pending=1, expected=1)

        # find and block this using bgp1
        block = self.client.get("/bhr/api/queue/bgp1").data[0]
        self.client.post(block['set_blocked'], dict(ident='bgp1'))

        check_counts(pending=0, current=1, expected=1)

        q = self.client.get("/bhr/api/queue/bgp1").data
        self.assertEqual(len(q), 0, "now that it's blocked, there should be no queue for bgp1")

        q = self.client.get("/bhr/api/queue/bgp2").data
        self.assertEqual(len(q), 1, "but there should be a queue entry for bgp2")

        # block it via bgp2
        block = self.client.get("/bhr/api/queue/bgp2").data[0]
        self.client.post(block['set_blocked'], dict(ident='bgp2'))

        check_counts(pending=0, current=1, expected=1)

        #now, wait 6 seconds, and see what's up

        sleep(6)

        check_counts(pending=0, current=1, expected=0)

        #now we should have some unblock queue entries
        q = self.client.get("/bhr/api/unblock_queue/bgp1").data
        self.assertEqual(len(q), 1)

        #unblock it

        self.client.post(q[0]['set_unblocked'])

        #we should still have 1 current block
        check_counts(pending=0, current=1, expected=0)

        #do the unblock for bgp2
        q = self.client.get("/bhr/api/unblock_queue/bgp2").data
        self.client.post(q[0]['set_unblocked'])

        #now we should have 0 blocks
        check_counts(pending=0, current=0, expected=0)

        #make sure there is nothing in the block or unblock queue for bgp1 bgp2.
        q = self.client.get("/bhr/api/queue/bgp1").data
        self.assertEqual(len(q), 0, "there should be no queue for bgp1")
        q = self.client.get("/bhr/api/unblock_queue/bgp1").data
        self.assertEqual(len(q), 0, "there should be no unblock queue for bgp1")

        q = self.client.get("/bhr/api/queue/bgp2").data
        self.assertEqual(len(q), 0, "there should be no queue for bgp2")
        q = self.client.get("/bhr/api/unblock_queue/bgp2").data
        self.assertEqual(len(q), 0, "there should be no unblock queue for bgp2")

    def test_list_csv(self):
        self._add_block(duration=30)

        csv_txt= self.client.get("/bhr/list.csv").content

        data = list(csv.DictReader(csv_txt.splitlines()))

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['who'], "admin")
        self.assertEqual(data[0]['why'], "testing")
        self.assertEqual(data[0]['source'], "test")

    def test_set_blocked_multi(self):
        self._add_block('1.2.3.4')
        self._add_block('4.3.2.1')

        blocks = self.client.get("/bhr/api/queue/bgp1").data

        ids = [b['id'] for b in blocks]
        data = json.dumps({"ids": ids})
        self.client.post("/bhr/api/set_blocked_multi/bgp1", data=data, content_type="application/json").data

        q = self.client.get("/bhr/api/queue/bgp1").data
        self.assertEqual(len(q), 0)

    def test_set_unblocked_multi(self):
        self._add_block('1.2.3.4', duration=2)
        self._add_block('4.3.2.1', duration=2)

        #as above
        blocks = self.client.get("/bhr/api/queue/bgp1").data
        ids = [b['id'] for b in blocks]
        data = json.dumps({"ids": ids})
        self.client.post("/bhr/api/set_blocked_multi/bgp1", data=data, content_type="application/json").data

        q = self.client.get("/bhr/api/queue/bgp1").data
        self.assertEqual(len(q), 0)

        #now wait...
        sleep(4)

        #grab queue
        blocks = self.client.get("/bhr/api/unblock_queue/bgp1").data
        self.assertEqual(len(blocks), 2)

        #send set unblocked request
        ids = [b['id'] for b in blocks]
        data = json.dumps({"ids": ids})
        self.client.post("/bhr/api/set_unblocked_multi", data=data, content_type="application/json").data

        #check result
        blocks = self.client.get("/bhr/api/unblock_queue/bgp1").data
        self.assertEqual(len(blocks), 0)

    def test_stats(self):
        self._add_block('1.2.3.4', duration=2)
        self._add_block('4.3.2.1', duration=2)
        stats = self.client.get("/bhr/api/stats").data

        self.assertEqual(stats['expected'], 2)
