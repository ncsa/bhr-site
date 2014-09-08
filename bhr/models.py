from django.contrib.auth.models import User
from django.db import models

from netfields import CidrAddressField, NetManager

from django.utils import timezone

class WhitelistError(Exception):
    pass

def is_whitelisted(cidr):
    for item in WhitelistEntry.objects.all():
        if cidr in item.cidr:
            return item
    return False

class WhitelistEntry(models.Model):
    cidr = CidrAddressField()
    who = models.ForeignKey(User, editable=False)
    why = models.TextField()
    added = models.DateTimeField('date added', auto_now_add=True)

FLAG_NONE     = "N"
FLAG_INBOUND  = "I"
FLAG_OUTBOUND = "O"
FLAG_BOTH     = "B"

class BlockEntry(models.Model):

    FLAG_DIRECTIONS = (
        (FLAG_NONE, 'None'),
        (FLAG_INBOUND, 'Inbound'),
        (FLAG_OUTBOUND, 'Outbound'),
        (FLAG_BOTH, 'Both'),
    )

    cidr = CidrAddressField()
    who  = models.ForeignKey(User, editable=False)
    source = models.CharField(max_length=30)
    why  = models.TextField()

    added = models.DateTimeField('date added', auto_now_add=True)
    unblock_at = models.DateTimeField('date to be unblocked', null=True)

    flag = models.CharField(max_length=1, choices=FLAG_DIRECTIONS, default=FLAG_NONE)

    skip_whitelist = models.BooleanField(default=False)

    forced_unblock  = models.BooleanField(default=False)
    unblock_why = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if not self.skip_whitelist:
            wle = is_whitelisted(self.cidr)
            if wle:
                raise WhitelistError(wle.why)
        super(BlockEntry, self).save(*args, **kwargs)


class Block(models.Model):
    entry = models.ForeignKey(BlockEntry)
    ident = models.CharField("blocker ident", max_length=50)

    added   = models.DateTimeField('date added')
    removed =  models.DateTimeField('date removed', null=True)

    class Meta:
        unique_together = ('entry', 'ident')

class BlockManager(object):
    def __init__(self):
        pass

    def get_block(self, cidr):
        """Get an existing block record"""
        BlockEntry.objects

    def add_block(self, cidr, who, source, why, unblock_at, duration):
        if duration:
            unblock_at = timezone.now() + datetime.timedelta(seconds=duration)

        b = BlockEntry(cidr=cidr, who=who, source=source, why=why, unblock_at=unblock_at)
        b.save()
        return b

