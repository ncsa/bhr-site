# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('bhr', '0005_block_unblock_who'),
    ]

    operations = [
        migrations.CreateModel(
            name='SourceBlacklistEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('source', models.CharField(unique=True, max_length=30)),
                ('why', models.TextField()),
                ('added', models.DateTimeField(auto_now_add=True, verbose_name=b'date added')),
                ('who', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
