from django_pglocks import advisory_lock

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Q
from django.db import transaction, connection

from netfields import CidrAddressField
import ipaddress

from django.utils import timezone
import datetime
import time

from django.conf import settings

from urllib import quote
import logging

from bhr.util import expand_time, resolve, ip_family

logger = logging.getLogger(__name__)

class WhitelistError(Exception):
    pass

class PrefixLenTooSmallError(Exception):
    pass

class SourceBlacklistedError(Exception):
    pass

def is_whitelisted(cidr):
    cidr = ipaddress.ip_network(unicode(cidr))
    for item in WhitelistEntry.objects.all():
        if cidr[0] in item.cidr or cidr[-1] in item.cidr:
            return item
        if item.cidr[0] in cidr or item.cidr[-1] in cidr:
            return item
    return False

def is_prefixlen_too_small(cidr):
    family = ip_family(cidr)
    if family == 4:
        minimum_prefixlen = settings.BHR.get('minimum_prefixlen', 24)
    else:
        minimum_prefixlen = settings.BHR.get('minimum_prefixlen_v6', 64)
    cidr = ipaddress.ip_network(unicode(cidr))
    return cidr.prefixlen < minimum_prefixlen

def is_source_blacklisted(source):
    try :
        entry = SourceBlacklistEntry.objects.get(source=source)
        return entry
    except ObjectDoesNotExist:
        return False

class WhitelistEntry(models.Model):
    cidr = CidrAddressField()
    who = models.ForeignKey(User)
    why = models.TextField()
    added = models.DateTimeField('date added', auto_now_add=True)

class SourceBlacklistEntry(models.Model):
    source = models.CharField(max_length=30, unique=True)
    who = models.ForeignKey(User)
    why = models.TextField()
    added = models.DateTimeField('date added', auto_now_add=True)

class CurrentBlockManager(models.Manager):
    def get_queryset(self):
        return super(CurrentBlockManager, self).get_queryset().filter(
            id__in = BlockEntry.objects.distinct('block_id').filter(removed__isnull=True).values_list('block_id', flat=True))

class ExpectedBlockManager(models.Manager):
    def get_queryset(self):
        return super(ExpectedBlockManager, self).get_queryset().filter(
            Q(unblock_at__gt=timezone.now()) |
            Q(unblock_at__isnull=True)
        ).exclude(
            forced_unblock=True,
        )

class PendingBlockManager(models.Manager):
    def get_queryset(self):
        return super(PendingBlockManager, self).get_queryset().filter(
            Q(unblock_at__gt=timezone.now()) |
            Q(unblock_at__isnull=True)
        ).exclude(
            forced_unblock=True,
        ).exclude(
            id__in = BlockEntry.objects.distinct('block_id').filter(removed__isnull=True).values_list('block_id', flat=True)
        )
class PendingRemovalBlockManager(models.Manager):
    def get_queryset(self):
        return super(PendingRemovalBlockManager, self).get_queryset().filter(
            id__in = BlockEntry.objects.distinct('block_id').filter(removed__isnull=True, unblock_at__lte=timezone.now()).values_list('block_id', flat=True)
        ).order_by('unblock_at')

class ExpiredBlockManager(models.Manager):
    def get_queryset(self):
        return super(ExpiredBlockManager, self).get_queryset().filter(
            Q(unblock_at__lt=timezone.now()) |
            Q(forced_unblock=True)
        )

FLAG_NONE     = "N"
FLAG_INBOUND  = "I"
FLAG_OUTBOUND = "O"
FLAG_BOTH     = "B"

class Block(models.Model):

    FLAG_DIRECTIONS = (
        (FLAG_NONE, 'None'),
        (FLAG_INBOUND, 'Inbound'),
        (FLAG_OUTBOUND, 'Outbound'),
        (FLAG_BOTH, 'Both'),
    )

    cidr = CidrAddressField(db_index=True)
    who  = models.ForeignKey(User)
    source = models.CharField(max_length=30, db_index=True)
    why  = models.TextField()

    added = models.DateTimeField('date added', auto_now_add=True, db_index=True)
    unblock_at = models.DateTimeField('date to be unblocked', null=True, db_index=True)

    flag = models.CharField(max_length=1, choices=FLAG_DIRECTIONS, default=FLAG_NONE)

    skip_whitelist = models.BooleanField(default=False)

    forced_unblock  = models.BooleanField(default=False)
    unblock_why = models.TextField(blank=True)
    unblock_who = models.ForeignKey(User, related_name='+', null=True, blank=True)

    objects = models.Manager()
    current = CurrentBlockManager()
    expected = ExpectedBlockManager()
    pending = PendingBlockManager()
    pending_removal = PendingRemovalBlockManager()
    expired = ExpiredBlockManager()

    def save(self, *args, **kwargs):
        if self.skip_whitelist is False and self.forced_unblock is False:
            wle = is_whitelisted(self.cidr)
            if wle:
                raise WhitelistError(wle.why)
            if is_prefixlen_too_small(self.cidr):
                raise PrefixLenTooSmallError("Prefix length in %s is too small" % self.cidr)
            item = is_source_blacklisted(self.source)
            if item:
                raise SourceBlacklistedError("Source %s is blacklisted: %s: %s" % (self.source, item.who, item.why))
        super(Block, self).save(*args, **kwargs)

    @property
    def is_unblockable(self):
        """Is this block record unblockable?
        This is not the same as if it IS blocked, but more "should this be blocked"
        """
        if self.forced_unblock:
            return False

        if self.unblock_at is None:
            return True

        if self.unblock_at > timezone.now():
            return True

        return False

    @property
    def duration(self):
        if self.unblock_at is None:
            return None
        return self.unblock_at - self.added

    @property
    def age(self):
        if self.unblock_at is None:
            return None
        return timezone.now() - self.unblock_at

    def unblock_now(self, who, why):
        logger.info("UNBLOCK_NOW ID=%s IP=%s", self.id, self.cidr)
        self.forced_unblock = True
        self.unblock_who = who
        self.unblock_why = why
        now = timezone.now()
        self.unblock_at = now
        BlockEntry.objects.filter(block_id=self.id).update(unblock_at=now)
        self.save()

class BlockEntry(models.Model):
    block = models.ForeignKey(Block)

    ident = models.CharField("blocker ident", max_length=50, db_index=True)

    added   = models.DateTimeField('date added', auto_now_add=True)
    removed =  models.DateTimeField('date removed', null=True)

    #Denormalized from Block
    unblock_at = models.DateTimeField('date to be unblocked', null=True, db_index=True)

    class Meta:
        unique_together = ('block', 'ident')

    def set_unblocked(self):
        self.removed = timezone.now()

    @classmethod
    def set_unblocked_by_id(self, id):
        BlockEntry.objects.filter(pk=id).update(removed=timezone.now())

class BHRDB(object):
    def __init__(self):
        pass

    def current(self):
        return Block.current
    
    def expected(self):
        return Block.expected

    def pending(self):
        return Block.pending

    def pending_removal(self):
        return Block.pending_removal

    def expired(self):
        return Block.expired

    def get_block(self, cidr):
        """Get an existing block record"""
        return Block.expected.filter(cidr=cidr).first()

    def get_last_block(self, cidr):
        """Get most recent block record"""
        return Block.objects.filter(cidr=cidr).order_by('-added').first()

    def get_last_block_duration(self, cidr):
        """Get most recent block record duration"""
        rec = self.get_last_block(cidr)
        return rec.duration

    def scale_duration(self, age, duration):
        minimum_time_window = settings.BHR['minimum_time_window']
        time_window_factor = settings.BHR['time_window_factor']
        penalty_time_multiplier = settings.BHR['penalty_time_multiplier']
        return_to_base_multiplier = settings.BHR['return_to_base_multiplier']
        return_to_base_factor = settings.BHR['return_to_base_factor']

        duration = round(duration)

        #short time frame repeat offender
        if age <= max(minimum_time_window, time_window_factor * duration):
            return penalty_time_multiplier * duration

        #medium time frame repeat offender
        if age <= time_window_factor * return_to_base_multiplier * duration:
            return duration

        #regular repeat offender
        return duration/return_to_base_factor;

    def add_block_multi(self, who, blocks):
        created = []
        with advisory_lock("add_block"), transaction.atomic():
            for block in blocks:
                b = self.add_block(who=who, **block)
                created.append(b)
        return created

    def add_block(self, cidr, who, source, why, duration=None, unblock_at=None, skip_whitelist=False, extend=True, autoscale=False):
        if duration:
            duration = expand_time(duration)

        now = timezone.now()
        if duration and not unblock_at:
            unblock_at = now + datetime.timedelta(seconds=duration)

        with advisory_lock("add_block") as acquired, transaction.atomic():
            b = self.get_block(cidr)
            if b:
                if extend is False or b.unblock_at is None or (unblock_at and unblock_at <= b.unblock_at):
                    logger.info('DUPE IP=%s', cidr)
                    return b
                b.unblock_at = unblock_at
                BlockEntry.objects.filter(block_id=b.id).update(unblock_at=unblock_at)
                logger.info('EXTEND IP=%s time extended UNTIL=%s DURATION=%s', cidr, unblock_at, duration)
                b.save()
                return b

            if duration and autoscale:
                lb = self.get_last_block(cidr)
                if lb and lb.duration:
                    last_duration = lb.duration and lb.duration.total_seconds() or duration
                    scaled_duration = max(duration, self.scale_duration(lb.age.total_seconds(), last_duration))
                    logger.info("Scaled duration from %d to %d", duration, scaled_duration)
                    duration = scaled_duration
                    unblock_at = now + datetime.timedelta(seconds=duration)

            b = Block(cidr=cidr, who=who, source=source, why=why, added=now, unblock_at=unblock_at, skip_whitelist=skip_whitelist)
            b.save()

            #It is possible that a block is added, and then after it expires, but before it is unblocked, a new block is added for that entry.
            #In that case, allow the new block (since we don't know if a backend may have already unblocked the old one)
            #but set the old record as already unblocked.  This should prevent a "block,block,unblock" timeline that results in the address
            #ending up not actually blocked.
            pending_unblock_records = BlockEntry.objects.filter(removed__isnull=True, block__cidr=cidr).all()
            for e in pending_unblock_records:
                e.set_unblocked()
                e.save()

        quoted_why = quote(why.encode('ascii', 'ignore'))
        logger.info('BLOCK IP=%s WHO=%s SOURCE=%s WHY=%s UNTIL="%s" DURATION=%s', cidr, who, source, quoted_why, unblock_at, duration)
        return b

    def unblock_now(self, cidr, who, why):
        b = self.get_block(cidr)
        if not b:
            raise Exception("%s is not blocked" % cidr)

        b.unblock_now(who, why)

    def set_blocked(self, b, ident):
        logger.info("SET_BLOCKED ID=%s IP=%s IDENT=%s", b.id, b.cidr, ident)
        return b.blockentry_set.create(ident=ident, unblock_at=b.unblock_at)

    def set_unblocked(self, b, ident):
        b = b.blockentry_set.get(ident=ident)
        b.set_unblocked()
        b.save()
        logger.info("SET_UNBLOCKED ID=%s IP=%s IDENT=%s", b.block.id, b.block.cidr, ident)

    def set_unblocked_by_blockentry_id(self, block_id):
        b = BlockEntry.objects.get(pk=block_id)
        b.set_unblocked()
        b.save()

    def block_queue(self, ident, limit=200, added_since='2014-09-01'):
        return Block.objects.raw("""
            SELECT b.id as pk, * from bhr_block b
            LEFT JOIN bhr_blockentry be
            ON b.id=be.block_id AND be.ident = %s
            WHERE
                b.added >= %s
            AND
                (b.unblock_at IS NULL OR
                 b.unblock_at > %s)
            AND
                b.forced_unblock is false
            AND
                be.added IS NULL AND be.removed is NULL
            ORDER BY
                b.added ASC
            LIMIT %s """,

            [ident, added_since, timezone.now(), limit]
        )

    def unblock_queue(self, ident):
        return BlockEntry.objects.filter(
            removed__isnull=True,
            ident=ident,
            unblock_at__lte=timezone.now(),
        ).order_by('unblock_at')

    def set_blocked_multi(self, ident, ids):
        with transaction.atomic():
            for id in ids:
                block = Block.objects.get(pk=id)
                block.blockentry_set.create(ident=ident, unblock_at=block.unblock_at)
                logger.info("SET_BLOCKED ID=%s IP=%s IDENT=%s", id, block.cidr, ident)

    def set_unblocked_multi(self, ids):
        with transaction.atomic():
            for id in ids:
                BlockEntry.set_unblocked_by_id(id)
                logger.info("SET_UNBLOCKED ID=%s", id)

    def get_history(self, query):
        if query[0].isdigit(): #assume cidr block
            return Block.objects.filter(cidr__in_cidr=query).select_related('who').order_by('-added')
        else:
            return Block.objects.filter(why__contains=query).select_related('who').order_by('-added')

    def stats(self):
        ret = {}
        ret['block_pending'] = self.pending().count()
        ret['unblock_pending'] = self.pending_removal().count()
        ret['current'] = self.current().count()
        ret['expected'] = self.expected().count()

        return ret

    def source_stats(self):
        stats = {}
        with connection.cursor() as c:
            c.execute('''SELECT source, count(source) from bhr_block
                WHERE (unblock_at > now() OR unblock_at IS NULL)
                AND forced_unblock=false
                GROUP BY source
                ORDER BY source ASC''')
            for source, count in c.fetchall():
                stats[source] = count
        return stats


def filter_local_networks(query):
    local_nets = settings.BHR.get("local_networks", [])
    if not local_nets:
        return Block.objects.none()
    q = Q()
    for n in local_nets:
        q |= Q(cidr__in_cidr=n)
    return query.filter(q)

class InCidr(models.Lookup):
    lookup_name = "in_cidr"

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return '%s <<= %s' % (lhs, rhs), params

models.fields.Field.register_lookup(InCidr)
