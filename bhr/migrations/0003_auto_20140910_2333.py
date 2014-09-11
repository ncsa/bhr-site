# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import netfields.fields
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('bhr', '0002_auto_20140908_2307'),
    ]

    operations = [
        migrations.AlterField(
            model_name='block',
            name='cidr',
            field=netfields.fields.CidrAddressField(max_length=43, db_index=True),
        ),
        migrations.AlterField(
            model_name='block',
            name='source',
            field=models.CharField(max_length=30, db_index=True),
        ),
        migrations.AlterField(
            model_name='block',
            name='who',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='whitelistentry',
            name='who',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
        ),
    ]
