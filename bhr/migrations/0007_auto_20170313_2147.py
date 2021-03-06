# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2017-03-13 21:47
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bhr', '0006_sourceblacklistentry'),
    ]

    operations = [
        migrations.AlterField(
            model_name='block',
            name='forced_unblock',
            field=models.BooleanField(default=False),
        ),
        migrations.RunSQL('CREATE INDEX bhr_block_forced_unblocked_true ON bhr_block (forced_unblock) WHERE forced_unblock=true'),
    ]
