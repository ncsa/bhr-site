from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.db import transaction

from netfields import CidrAddressField
from netaddr import IPNetwork

from django.utils import timezone
import datetime

from django.conf import settings

import logging

from bhr.util import expand_time

logger = logging.getLogger(__name__)

class WhitelistError(Exception):
    pass

def is_whitelisted(cidr):
    cidr = IPNetwork(cidr)
    for item in WhitelistEntry.objects.all():
        if cidr in item.cidr or item.cidr in cidr:
            return item
    return False

class WhitelistEntry(models.Model):
    cidr = CidrAddressField()
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
            Q(unblock_at__lt=timezone.now()) |
            Q(forced_unblock=True)
        ).filter(
            id__in = BlockEntry.objects.distinct('block_id').filter(removed__isnull=True).values_list('block_id', flat=True)
        )

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

    added = models.DateTimeField('date added', auto_now_add=True)
    unblock_at = models.DateTimeField('date to be unblocked', null=True, db_index=True)

    flag = models.CharField(max_length=1, choices=FLAG_DIRECTIONS, default=FLAG_NONE)

    skip_whitelist = models.BooleanField(default=False)

    forced_unblock  = models.BooleanField(default=False, db_index=True)
    unblock_why = models.TextField(blank=True)

    objects = models.Manager()
    current = CurrentBlockManager()
    expected = ExpectedBlockManager()
    pending = PendingBlockManager()
    pending_removal = PendingRemovalBlockManager()
    expired = ExpiredBlockManager()

    def save(self, *args, **kwargs):
        if not self.skip_whitelist:
            wle = is_whitelisted(self.cidr)
            if wle:
                raise WhitelistError(wle.why)
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

    def unblock_now(self, why):
        self.forced_unblock = True
        self.unblock_why = why
        self.save()

class BlockEntry(models.Model):
    block = models.ForeignKey(Block)
    ident = models.CharField("blocker ident", max_length=50, db_index=True)

    added   = models.DateTimeField('date added', auto_now_add=True)
    removed =  models.DateTimeField('date removed', null=True, db_index=True)

    class Meta:
        unique_together = ('block', 'ident')

    def set_unblocked(self):
        self.removed = timezone.now()

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

    def add_block(self, cidr, who, source, why, duration=None, unblock_at=None, skip_whitelist=False, autoscale=False):
        b = self.get_block(cidr)
        if b:
            return b

        if duration:
            duration = expand_time(duration)

        if duration and autoscale:
            lb = self.get_last_block(cidr)
            if lb:
                scaled_duration = max(duration, self.scale_duration(lb.age.total_seconds(), lb.duration.total_seconds()))
                logger.info("Scaled duration from %d to %d", duration, scaled_duration)
                print "Scaled duration from %d to %d" % (duration, scaled_duration)
                duration = scaled_duration

        now = timezone.now()
        if duration and not unblock_at:
            unblock_at = now + datetime.timedelta(seconds=duration)

        b = Block(cidr=cidr, who=who, source=source, why=why, added=now, unblock_at=unblock_at, skip_whitelist=skip_whitelist)
        b.save()
        return b

    def unblock_now(self, cidr, why):
        b = self.get_block(cidr)
        if not b:
            raise Exception("%s is not blocked" % cidr)

        b.unblock_now(why)

    def set_blocked(self, b, ident):
        return b.blockentry_set.create(ident=ident)

    def set_unblocked(self, b, ident):
        b = b.blockentry_set.get(ident=ident)
        b.set_unblocked()
        b.save()

    def set_unblocked_by_blockentry_id(self, block_id):
        b = BlockEntry.objects.get(pk=block_id)
        b.set_unblocked()
        b.save()

    def block_queue(self, ident, limit=200):
        return list(Block.objects.raw("""
            SELECT b.id as pk, * from bhr_block b
            LEFT JOIN bhr_blockentry be
            ON b.id=be.block_id AND be.ident = %s
            WHERE
                (b.unblock_at IS NULL OR
                 b.unblock_at > %s)
            AND
                b.forced_unblock is false
            AND
                be.added IS NULL
            LIMIT %s """,

            [ident, timezone.now(), limit]
        ))

    def unblock_queue(self, ident):
        return BlockEntry.objects.filter(removed__isnull=True, ident=ident).filter(
            block_id__in = self.expired().values_list('id', flat=True))

    def set_blocked_multi(self, ident, ids):
        with transaction.atomic():
            for id in ids:
                block = Block.objects.get(pk=id)
                block.blockentry_set.create(ident=ident)

    def set_unblocked_multi(self, ids):
        with transaction.atomic():
            for id in ids:
                entry = BlockEntry.objects.get(pk=id)
                entry.set_unblocked()
                entry.save()

    def get_history(self, cidr):
        return Block.objects.filter(cidr__in_cidr=cidr).select_related('who').order_by('-added')

    def stats(self):
        ret = {}
        ret['block_pending'] = self.pending().count()
        ret['unblock_pending'] = self.pending_removal().count()
        ret['current'] = self.current().count()
        ret['expected'] = self.expected().count()

        return ret


class InCidr(models.Lookup):
    lookup_name = "in_cidr"

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return '%s <<= %s' % (lhs, rhs), params

models.fields.Field.register_lookup(InCidr)
