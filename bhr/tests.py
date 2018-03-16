from django.contrib.auth.models import User, Permission
from django.test import TestCase, override_settings
from django.utils import timezone
import dateutil.parser
import datetime
import ipaddress
import json
import csv

from bhr.models import BHRDB, Block, WhitelistEntry, SourceBlacklistEntry, is_whitelisted, is_prefixlen_too_small, is_source_blacklisted, filter_local_networks
from bhr.util import expand_time, ip_family

# Create your tests here.

class DBTests(TestCase):
    def setUp(self):
        self.db = BHRDB()
        self.user = User.objects.create_user('admin', 'a@b.com', 'admin')

    def test_non_existing_block_is_none(self):
        b = self.db.get_block('1.2.3.4')
        self.assertEqual(b, None)

    def test_adding_a_block_works(self):
        b = self.db.add_block('1.2.3.4/32', self.user, 'test', 'testing')
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
        q = list(self.db.block_queue('bgp1'))
        self.assertEqual(len(q), 0)

    def test_block_queue(self):
        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing')

        q = list(self.db.block_queue('bgp1'))

        self.assertEqual(len(q), 1)
        self.assertEqual(str(q[0].cidr), '1.2.3.4/32')

        self.db.set_blocked(b1, 'bgp1')

        q = list(self.db.block_queue('bgp1'))

        self.assertEqual(len(q), 0)

    def test_block_two_blockers(self):
        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing')

        for ident in 'bgp1', 'bgp2':
            q = list(self.db.block_queue(ident))
            self.assertEqual(len(q), 1)
            self.assertEqual(str(q[0].cidr), '1.2.3.4/32')

        self.db.set_blocked(b1, 'bgp1')
        self.db.set_blocked(b1, 'bgp2')

        for ident in 'bgp1', 'bgp2':
            q = list(self.db.block_queue(ident))
            self.assertEqual(len(q), 0)

    def test_block_two_blockers_only_one(self):
        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing')

        self.db.set_blocked(b1, 'bgp1')

        q = list(self.db.block_queue('bgp1'))
        self.assertEqual(len(q), 0)

        q = list(self.db.block_queue('bgp2'))
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

        self.db.unblock_now('1.2.3.4', self.user, 'testing')

        expected = self.db.expected().all()
        self.assertEqual(len(expected), 0)

    def test_unblock_now_moves_to_pending_removal(self):
        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing')
        self.db.unblock_now('1.2.3.4', self.user, 'testing')
        b1.refresh_from_db()

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

        self.db.unblock_now('1.2.3.4', self.user, 'testing')

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
        self.db.unblock_now('1.2.3.4', self.user, 'testing')

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

        self.db.unblock_now('1.2.3.4', self.user, 'testing')
        check_counts(current=1, expected=0, unblock_pending=1)

        self.db.set_unblocked(b1, 'bgp1')
        check_counts()

    def test_source_stats(self):
        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing')

        self.assertEqual(self.db.source_stats(), {"test": 1})

        b1 = self.db.add_block('1.2.3.5', self.user, 'other', 'testing')
        b1 = self.db.add_block('1.2.3.6', self.user, 'other', 'testing')
        self.assertEqual(self.db.source_stats(), {"test": 1, "other": 2})

    def test_whitelist(self):
        WhitelistEntry(who=self.user, why='test', cidr='141.142.0.0/16').save()

        self.assertEqual(bool(is_whitelisted("1.2.3.4")), False)
        self.assertEqual(bool(is_whitelisted("1.2.3.0/24")), False)

        self.assertEqual(bool(is_whitelisted("141.142.2.2")), True)
        self.assertEqual(bool(is_whitelisted("141.142.4.0/24")), True)
        self.assertEqual(bool(is_whitelisted("141.0.0.0/8")), True)

    def test_block_then_whitelist_then_unblock_works(self):
        b1 = self.db.add_block('1.2.3.4', self.user, 'other', 'testing')
        WhitelistEntry(who=self.user, why='test', cidr='1.2.3.0/24').save()
        self.db.unblock_now('1.2.3.4', self.user, 'testing')

    @override_settings()
    def test_prefixlen_too_small(self):
        from django.conf import settings
        settings.BHR['minimum_prefixlen'] = 24
        self.assertEqual(is_prefixlen_too_small(u"1.2.3.4"), False)
        self.assertEqual(is_prefixlen_too_small(u"1.2.3.0/24"), False)
        self.assertEqual(is_prefixlen_too_small(u"1.2.0.0/20"), True)

        settings.BHR['minimum_prefixlen'] = 32
        self.assertEqual(is_prefixlen_too_small(u"1.2.3.0/24"), True)

    @override_settings()
    def test_prefixlen_too_small_v6(self):
        from django.conf import settings
        settings.BHR['minimum_prefixlen_v6'] = 64
        self.assertEqual(is_prefixlen_too_small(u"fe80::/32"), True)
        self.assertEqual(is_prefixlen_too_small(u"fe80::1/128"), False)

    def test_source_blacklisted(self):
        self.assertEqual(bool(is_source_blacklisted("test")), False)
        SourceBlacklistEntry(who=self.user, why='test', source='test').save()
        self.assertEqual(bool(is_source_blacklisted("test")), True)

    def test_filter_local(self):
        b1 = self.db.add_block('1.2.3.4', self.user, 'other', 'testing')
        local = filter_local_networks(self.db.expected())
        self.assertEqual(len(local), 0)

        b1 = self.db.add_block('10.2.3.4', self.user, 'other', 'testing')
        local = filter_local_networks(self.db.expected())
        self.assertEqual(len(local), 1)

    @override_settings()
    def test_filter_local_unset(self):
        from django.conf import settings
        del settings.BHR['local_networks']
        b1 = self.db.add_block('1.2.3.4', self.user, 'other', 'testing')
        local = filter_local_networks(self.db.expected())
        self.assertEqual(len(local), 0)

        b1 = self.db.add_block('10.2.3.4', self.user, 'other', 'testing')
        local = filter_local_networks(self.db.expected())
        self.assertEqual(len(local), 0)

class ScalingTests(TestCase):
    def setUp(self):
        self.db = BHRDB()
        self.user = User.objects.create_user('admin', 'a@b.com', 'admin')

    def add_older_block(self, age, duration):
        now = timezone.now()
        before = now - datetime.timedelta(seconds=age)
        unblock_at = before + datetime.timedelta(seconds=duration)
        b = Block(cidr='1.2.3.4', who=self.user, source='test', why='test', unblock_at=unblock_at)
        b.save()
        b.added = before
        b.save()
        self.db.set_blocked(b, 'bgp1')
        self.db.set_unblocked(b, 'bgp1')
        return b

    def test_get_last_block(self):
        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing', duration=10)
        lb = self.db.get_last_block('1.2.3.4')

        self.assertAlmostEqual(lb.duration.total_seconds(), 10, places=1)

    def test_that_scaling_doesnt_break_with_manual_unblock(self):
        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing', duration=None)
        self.db.unblock_now('1.2.3.4', self.user, 'testing')
        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing', duration=300, autoscale=True)

    def scale_test(self, age, duration, new_duration, expected_duration):
        b = self.add_older_block(age, duration)
        b1 = self.db.add_block('1.2.3.4', self.user, 'test', 'testing', duration=new_duration, autoscale=True)
        lb = self.db.get_last_block('1.2.3.4')
        self.assertAlmostEqual(lb.duration.total_seconds(), expected_duration, places=1)

    def test_block_scaled_short(self):
        self.scale_test(
            age=60*60,
            duration=60*5,
            new_duration=60*5,
            expected_duration=60*10)

    def test_block_scaled_medium(self):
        self.scale_test(
            age=60*60*24*4,
            duration=60*60*24,
            new_duration=60*60,
            expected_duration=60*60*24)


from rest_framework.test import APITestCase
from rest_framework import status
from time import sleep

class ApiTest(TestCase):
    def setUp(self):
        self.user = user = User.objects.create_user('admin', 'temporary@gmail.com', 'admin')
        self.client.login(username='admin', password='admin')
        for perm in 'add_block change_block add_blockentry change_blockentry'.split():
            self.user.user_permissions.add(Permission.objects.get(codename=perm))

    def _add_block(self, cidr='1.2.3.4', duration=30, skip_whitelist=0,source='test', extend=False, why='testing'):
        return self.client.post('/bhr/api/block', dict(
            cidr=cidr,
            source=source,
            why=why,
            duration=duration,
            skip_whitelist=skip_whitelist,
            extend=extend,
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

    def test_block_source_blacklist(self):
        SourceBlacklistEntry(who=self.user, why='test', source='test').save()
        response = self._add_block()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self._add_block(skip_whitelist=True)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_block_prefixlen_too_small(self):
        response = self._add_block(cidr='1.0.0.0/8')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self._add_block(cidr='1.0.0.0/8', skip_whitelist=True)
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

    def test_unblock_now(self):
        self._add_block(cidr='1.2.3.11',why='testing unblock now')

        block = self.client.get("/bhr/api/queue/bgp1").data[0]
        self.client.post(block['set_blocked'], dict(ident='bgp1'))

        q = self.client.get("/bhr/api/unblock_queue/bgp1").data
        self.assertEqual(len(q), 0)

        self.client.post("/bhr/api/unblock_now", dict(cidr="1.2.3.11", why="testing"))

        q = self.client.get("/bhr/api/unblock_queue/bgp1").data
        self.assertEqual(len(q), 1)

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

    def test_history_limited(self):
        self._add_block()
        self.client.logout()
        hist = self.client.get("/bhr/api/query_limited/1.2.3.4").data
        self.assertEqual(len(hist), 1)
        self.assertNotIn('who', hist[0])
        self.assertNotIn('why', hist[0])

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

    def test_list_csv_since(self):
        self._add_block(cidr='1.1.1.1', duration=30, why='block 1')
        sleep(.1)
        self._add_block(cidr='1.1.1.2', duration=30, why='block 2')

        csv_txt = self.client.get("/bhr/list.csv").content
        data = list(csv.DictReader(csv_txt.splitlines()))

        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['why'], "block 1")
        self.assertEqual(data[1]['why'], "block 2")

        added = data[-1]['added']
        sleep(.1)
        self._add_block(cidr='1.1.1.3', duration=30, why='block 3')

        # due to the use of >= this will get the last record again
        csv_txt = self.client.get("/bhr/list.csv", {'since': added}).content
        data = list(csv.DictReader(csv_txt.splitlines()))
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['why'], "block 2")
        self.assertEqual(data[1]['why'], "block 3")


    def test_list_csv_unicode_crap(self):
        unicode_crap = u'\u0153\u2211\xb4\xae\u2020\xa5\xa8\u02c6\xf8\u03c0\u201c\u2018'
        self._add_block(why=unicode_crap)
        csv_txt = self.client.get("/bhr/list.csv").content

        data = list(csv.DictReader(csv_txt.splitlines()))
        self.assertEqual(len(data), 1)

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

    def test_expected_source_filtering(self):
        self._add_block('1.1.1.1', source='one')
        self._add_block('2.2.2.1', source='two')
        self._add_block('2.2.2.2', source='two')
        
        blocks = self.client.get("/bhr/api/expected_blocks/").data
        self.assertEqual(len(blocks), 3)

        blocks = self.client.get("/bhr/api/expected_blocks/?source=one").data
        self.assertEqual(len(blocks), 1)

        blocks = self.client.get("/bhr/api/expected_blocks/?source=two").data
        self.assertEqual(len(blocks), 2)

    def test_double_block_race_condition(self):
        #Add a short block and make sure bgp1 has it as blocked
        self._add_block('1.1.1.1', source='one', duration=1)
        block = self.client.get("/bhr/api/queue/bgp1").data[0]
        self.client.post(block['set_blocked'], dict(ident='bgp1'))
        sleep(2)

        #now, it should be unblocked, so we can add a new one
        self._add_block('1.1.1.1', source='one', duration=20000)

        #at this point, to ensure that the block manager won't do a A:
        # BLOCK
        # BLOCK
        # UNBLOCK
        #We need to make sure that the original record does not show up in the unblock queue.
        blocks = self.client.get("/bhr/api/unblock_queue/bgp1").data
        self.assertEqual(len(blocks), 0)

    def test_block_extend_False(self):
        self._add_block('1.1.1.1', source='one', duration=60)
        self._add_block('1.1.1.1', source='one', duration=120, extend=False)
        block = self.client.get("/bhr/api/query/1.1.1.1").data[0]
        unblock_at = dateutil.parser.parse(block["unblock_at"])
        duration = (unblock_at - timezone.now()).seconds
        self.assertLess(duration, 118)

    def test_block_extend_True(self):
        self._add_block('1.1.1.1', source='one', duration=60)
        self._add_block('1.1.1.1', source='one', duration=120, extend=True)
        block = self.client.get("/bhr/api/query/1.1.1.1").data[0]
        unblock_at = dateutil.parser.parse(block["unblock_at"])
        duration = (unblock_at - timezone.now()).seconds
        self.assertGreater(duration, 118)

    def test_block_extend_True_from_infinite_does_not_replace(self):
        print self._add_block('1.1.1.1', source='one', duration=0)
        print self._add_block('1.1.1.1', source='one', duration=120, extend=True)
        block = self.client.get("/bhr/api/query/1.1.1.1").data[0]
        self.assertEqual(block['unblock_at'], None)

    def test_block_extend_True_from_infinite_with_infinite_does_not_crash(self):
        self._add_block('1.1.1.1', source='one', duration=0)
        self._add_block('1.1.1.1', source='one', duration=0, extend=True)

    def test_block_extend_to_infinite_works(self):
        self._add_block('1.1.1.1', source='one', duration=60)
        self._add_block('1.1.1.1', source='one', duration=0, extend=True)
        block = self.client.get("/bhr/api/query/1.1.1.1").data[0]
        self.assertEqual(block['unblock_at'], None)

class UtilTest(TestCase):
    def test_expand_time(self):
        cases = [
            ('10',      10),
            ('10s',     10),
            ('7m',      7*60),
            ('14m',     14*60),
            ('4h',      4*60*60),
            ('22h',     22*60*60),
            ('3d',      3*60*60*24),
            ('3mo',     3*60*60*24*30),
            ('2y',      2*60*60*24*365),
        ]

        for text, number in cases:
            self.assertEqual(expand_time(text), number)

    def test_ip_family(self):
        cases = [
            ('1.2.3.4', 4),
            ('fe80::69b:c5:78a1:5ead', 6),
            (ipaddress.ip_address(u'1.2.3.4'), 4),
        ]
        for ip, family in cases:
            self.assertEqual(ip_family(ip), family)

        self.assertRaises(ValueError, ip_family, "banana")
