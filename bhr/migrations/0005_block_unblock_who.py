# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('bhr', '0004_auto_20140911_1337'),
    ]

    operations = [
        migrations.AddField(
            model_name='block',
            name='unblock_who',
            field=models.ForeignKey(related_name=b'+', blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
    ]
