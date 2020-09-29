# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bhr', '0003_auto_20140910_2333'),
    ]

    operations = [
        migrations.AlterField(
            model_name='block',
            name='forced_unblock',
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.AlterField(
            model_name='block',
            name='unblock_at',
            field=models.DateTimeField(null=True, verbose_name='date to be unblocked', db_index=True),
        ),
        migrations.AlterField(
            model_name='blockentry',
            name='ident',
            field=models.CharField(max_length=50, verbose_name='blocker ident', db_index=True),
        ),
        migrations.AlterField(
            model_name='blockentry',
            name='removed',
            field=models.DateTimeField(null=True, verbose_name='date removed', db_index=True),
        ),
    ]
