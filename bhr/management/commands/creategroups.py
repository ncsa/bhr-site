from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError


def create_group_with_perms(group, perms):
    print "Creating %r group" % group
    group, created = Group.objects.get_or_create(name=group)
    for perm in perms:
        group.permissions.add(Permission.objects.get(codename=perm))

class Command(BaseCommand):
    help = 'Create initial BHR groups'

    def handle(self, *args, **options):
        print "Creating initial BHR Groups"

        print "Creating 'BHR Users' group"
        bhr_group, created = Group.objects.get_or_create(name='BHR Users')
        cts = ContentType.objects.filter(app_label='bhr')
        for p in Permission.objects.filter(content_type__in=cts):
            bhr_group.permissions.add(p)

        create_group_with_perms('BHR Block Managers', ['add_blockentry','change_blockentry'])
        create_group_with_perms('BHR Blockers', ['add_block'])
